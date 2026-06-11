import json
import logging
import time
from datetime import datetime, timezone

import redis

from app.core.config import settings
from app.schemas.task import ProgressEvent

logger = logging.getLogger(__name__)

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def reset_redis() -> None:
    global _redis
    _redis = None


def release_task_lock(task_id: str) -> None:
    get_redis().delete(f"lock:task:{task_id}")


def acquire_task_lock(task_id: str, ttl: int = 7200) -> bool:
    acquired = get_redis().set(f"lock:task:{task_id}", "1", nx=True, ex=ttl)
    if acquired:
        logger.info("Task lock acquired task_id=%s", task_id)
    else:
        logger.warning("Task lock busy task_id=%s", task_id)
    return bool(acquired)


def progress_channel(task_id: str) -> str:
    return f"task:{task_id}:events"


def progress_key(task_id: str) -> str:
    return f"task:{task_id}:progress"


def publish_progress(
    task_id: str,
    status: str,
    stage: str,
    progress: int,
    message: str,
    current_segment: int | None = None,
    total_segments: int | None = None,
) -> ProgressEvent:
    event = ProgressEvent(
        task_id=task_id,
        status=status,
        stage=stage,
        progress=progress,
        message=message,
        current_segment=current_segment,
        total_segments=total_segments,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    r = get_redis()
    data = event.model_dump_json()
    r.set(progress_key(task_id), data)
    r.publish(progress_channel(task_id), data)
    return event


class VideoConcurrencyLimiter:
    """Global semaphore limiting concurrent MiniMax video API calls (TTL-based slots)."""

    ACTIVE_PREFIX = "semaphore:minimax:video:active:"
    LOCK_TTL = 600

    def __init__(self, max_concurrent: int | None = None) -> None:
        self.max_concurrent = max_concurrent or settings.video_concurrency

    def _active_count(self, r: redis.Redis) -> int:
        return len(r.keys(f"{self.ACTIVE_PREFIX}*"))

    def acquire(self, holder_id: str, timeout: int = 3600) -> bool:
        r = get_redis()
        deadline = datetime.now(timezone.utc).timestamp() + timeout
        slot_key = f"{self.ACTIVE_PREFIX}{holder_id}"
        while datetime.now(timezone.utc).timestamp() < deadline:
            current = self._active_count(r)
            if current < self.max_concurrent:
                if r.set(slot_key, "1", nx=True, ex=self.LOCK_TTL):
                    logger.info("Video slot acquired holder=%s active=%d/%d", holder_id, current + 1, self.max_concurrent)
                    return True
            time.sleep(2)
        logger.warning("Video slot timeout holder=%s active=%d", holder_id, self._active_count(r))
        return False

    def release(self, holder_id: str) -> None:
        r = get_redis()
        slot_key = f"{self.ACTIVE_PREFIX}{holder_id}"
        if r.delete(slot_key):
            logger.info("Video slot released holder=%s active=%d", holder_id, self._active_count(r))


video_limiter = VideoConcurrencyLimiter()


class ImageConcurrencyLimiter(VideoConcurrencyLimiter):
    ACTIVE_PREFIX = "semaphore:minimax:image:active:"

    def __init__(self, max_concurrent: int | None = None) -> None:
        super().__init__(max_concurrent or settings.image_concurrency)


image_limiter = ImageConcurrencyLimiter()
