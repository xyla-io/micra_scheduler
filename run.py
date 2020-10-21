from gevent import monkey
monkey.patch_all()

import click
from environments import environment, set_environment
from micra_scheduler import Scheduler
from micra_store.user import run

scheduler = Scheduler(config=environment)
run.add_micra_commands(commands=list(filter(lambda c: c.can_run, scheduler.commands)))

if __name__ == '__main__':
  run()