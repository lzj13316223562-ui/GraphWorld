from __future__ import annotations

from redis import Redis
from rq import Queue
from rq.job import Job

from backend.app.core.config import get_settings

QUEUE_NAME = "graphworld-runs"


def redis_connection() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url)


def run_queue() -> Queue:
    return Queue(QUEUE_NAME, connection=redis_connection())


def enqueue_run(run_id: str) -> Job:
    return run_queue().enqueue(
        "backend.app.workers.jobs.run_agent_job",
        run_id,
        job_timeout="2h",
        result_ttl=86400,
        failure_ttl=86400,
    )
