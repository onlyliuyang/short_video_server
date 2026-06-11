import logging
import time
from datetime import datetime, timezone

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


class ProviderConcurrencyLimiter:
    """Per-provider Redis semaphore."""

    LOCK_TTL = 600

    def __init__(self, provider_id: str, max_concurrent: int) -> None:
        self.provider_id = provider_id
        self.max_concurrent = max_concurrent
        self.active_prefix = f"semaphore:provider:{provider_id}:active:"

    def _active_count(self, r: redis.Redis) -> int:
        return len(r.keys(f"{self.active_prefix}*"))

    def acquire(self, holder_id: str, timeout: int = 3600) -> bool:
        r = get_redis()
        deadline = datetime.now(timezone.utc).timestamp() + timeout
        slot_key = f"{self.active_prefix}{holder_id}"
        while datetime.now(timezone.utc).timestamp() < deadline:
            current = self._active_count(r)
            if current < self.max_concurrent:
                if r.set(slot_key, "1", nx=True, ex=self.LOCK_TTL):
                    logger.info(
                        "Provider slot acquired provider=%s holder=%s active=%d/%d",
                        self.provider_id, holder_id, current + 1, self.max_concurrent,
                    )
                    return True
            time.sleep(2)
        logger.warning(
            "Provider slot timeout provider=%s holder=%s active=%d",
            self.provider_id, holder_id, self._active_count(r),
        )
        return False

    def release(self, holder_id: str) -> None:
        r = get_redis()
        slot_key = f"{self.active_prefix}{holder_id}"
        if r.delete(slot_key):
            logger.info(
                "Provider slot released provider=%s holder=%s active=%d",
                self.provider_id, holder_id, self._active_count(r),
            )
