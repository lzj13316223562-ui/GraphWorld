from __future__ import annotations

from rq import Worker

from backend.app.workers.queue import QUEUE_NAME, redis_connection


def main() -> None:
    worker = Worker([QUEUE_NAME], connection=redis_connection())
    worker.work()


if __name__ == "__main__":
    main()
