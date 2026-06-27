"""app/celery_app.py"""
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "watchr",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.celery_tasks.scraping_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_routes={
        "app.celery_tasks.scraping_tasks.*": {"queue": "scraping"},
    },
    task_soft_time_limit=480,
    task_time_limit=540,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=7200,
)
