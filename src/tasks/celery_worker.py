"""
Celery Worker启动脚本

用于启动Celery Worker进程。
"""

import click
from celery import Celery
from celery.bin import worker

from .celery_app import celery_app


@click.command()
@click.option("--loglevel", default="info", help="Logging level")
@click.option("--queues", default="build,test,analysis,notification", help="Queue names")
@click.option("--concurrency", default=4, help="Number of worker processes")
def start_worker(loglevel: str, queues: str, concurrency: int):
    """启动Celery Worker"""
    worker_class = worker.worker(
        celery_app,
        loglevel=loglevel,
        queues=queues.split(","),
        concurrency=concurrency,
    )
    worker_class.start()


if __name__ == "__main__":
    start_worker()
