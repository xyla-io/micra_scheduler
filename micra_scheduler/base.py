from __future__ import annotations

import time
import json
import micra_store.structure

from redis import Redis
from hashlib import sha1
from typing import Dict, Optional, List
from micra_store import Coordinator, Listener, retry, Job, uuid
from micra_store.command import Command, StartCommand, StatusCommand, ListCommand, ViewCommand, QuitCommand
from .structure import longcat_api_requests

class Scheduler(Coordinator):
  @property
  def commands(self) -> List[Command]:
    return [
      StartCommand(all_names=['scheduler'], context=self),
      StatusCommand(context=self),
      ListCommand(context=self),
      ViewCommand(context=self),
      QuitCommand(context=self),
    ]

  def start_longcat_queue(self):
    r = self.redis

    @retry(pdb_enabled=self.pdb_enabled, queue=self.queue)
    def longcat_queue():
      while True:
        if r.llen('longcat_api_requests_to_score') >= 3:
          # sleep so that we don't block the scoring if requests are coming in fast
          time.sleep(0.01)
        else:
          r.brpoplpush('longcat_api_requests', 'longcat_api_requests_to_score')
          print('Pushing from requests to requests_to_score...')
          
    self.start_listener(longcat_queue)

  def start_longcat_scoring(self):
    r = self.redis

    @retry(pdb_enabled=self.pdb_enabled, queue=self.queue)
    def longcat_scoring():
      def score_request(pipe):
        requests = pipe.lrange('longcat_api_scoring_hopper', 0, 0)
        if requests:
          job = self.longcat_api_job(request=requests[0])
          scored_job_instance_key = f'scored_job_instance:{job._job_name}'
          pipe.watch(scored_job_instance_key)
          # handle invalid jobs
          if job is None:
            pipe.rpop('longcat_api_scoring_hopper')
            return
          # re-enque requests for jobs that are currently in progress
          if pipe.sismember('active_jobs', job._job_name):
            # TODO: check if the request job version matches the scored job version, and just take the minium score using a LUA script if so. 
            # More sophisticated implementations could examine the scored_job_instance_key and ready_jobs set and determine whether to score the job anyway and cause the MicraManager to cancel the current active run of the job
            pipe.rpoplpush('longcat_api_scoring_hopper', 'longcat_api_requests_to_score')
            return

          print(f'Created job: {job.configuration}')
          score = self.longcat_api_job_score(job=job)
          pipe.multi()
          job._put(pipe=pipe)
          pipe.zadd('almacen_scored_jobs', {job._job_name: score})
          pipe.sadd('active_jobs', job._job_name)
          pipe.set(scored_job_instance_key, job._name)
          pipe.rpop('longcat_api_scoring_hopper')
      while True:
        # we could sleep here instead in order to block until a request comes in without using another list
        if not r.llen('longcat_api_scoring_hopper'):
          r.brpoplpush('longcat_api_requests_to_score', 'longcat_api_scoring_hopper')
        r.transaction(score_request, 'longcat_api_scoring_hopper')

    self.start_listener(longcat_scoring)

  def start(self):
    for element in [
      longcat_api_requests,
    ]:
      self.define_structure(element)
    self.start_longcat_queue()
    self.start_longcat_scoring()
    super().start()

  def longcat_api_job(self, request: str) -> Job:
    def almacen_report_action(request_json: Dict[str, any]) -> str:
      if request_json['action'] == 'tag_update_ui':
        return 'mutate'
      else:
        return request_json['action']

    def almacen_report_target(request_json: Dict[str, any]) -> str:
      if request_json['action'] == 'tag_update_ui':
        return 'performance_cube_filtered'
      else:
        return 'all'

    def almacen_job_contents(request_json: Dict[str, any]) -> Optional[Dict[str, any]]:
      contents = {}
      contents['realm'] = 'almacen'
      contents['company'] = request_json['company']
      contents['action'] = almacen_report_action(request_json)
      contents['target'] = almacen_report_target(request_json)
      return contents

    try:
      request_json = json.loads(request)
    except json.decoder.JSONDecodeError:
      return None
    version = sha1(request.encode('utf-8')).hexdigest()
    job_name = Job.name_from_components([
      'job',
      'almacen',
      request_json['company'],
      request_json['action'],
      version,
      uuid(),
    ])
    job = Job(name=job_name, contents=almacen_job_contents(request_json))
    job.configuration = request_json['body']
    return job
  
  def longcat_api_job_score(self, job: Job) -> float:
    # Add seconds to the score if the job should be de-prioritized, for example if it is being repeated too often
    return time.time()
