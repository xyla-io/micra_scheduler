# micra_scheduler
Our codebase for receiving database-related events for triggering tasks to be run (WIP)

# setup info
- Need to have run the following command in `redis-cli` before using:
`xgroup create almacen_ready_jobs almacen_worker_group $ MKSTREAM`

# Testing

## Simulate a Longcat API request

```bash
redis-cli -x lpush longcat_api_requests < micra_scheduler/test/test_job.json
```
