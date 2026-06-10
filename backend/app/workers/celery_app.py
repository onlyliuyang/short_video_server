from celery import Celery
from celery.signals import worker_process_init

from app.core.config import settings
from app.utils.logging_config import setup_logging

setup_logging()

celery_app = Celery(
    "short_video_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    broker_connection_retry_on_startup=True,
    task_routes={
        "app.workers.tasks.generate_segment_video": {"queue": "video_gen"},
        "app.workers.tasks.generate_voiceover": {"queue": "tts"},
        "app.workers.tasks.compose_final_video": {"queue": "media"},
    },
)


@worker_process_init.connect
def _reset_worker_state(**kwargs) -> None:
    """Avoid forked workers reusing parent-process HTTP/Redis clients (macOS SIGSEGV)."""
    from app.services.llm_service import llm_service
    from app.utils.progress import reset_redis

    llm_service.reset()
    reset_redis()


celery_app.autodiscover_tasks(["app.workers"])
