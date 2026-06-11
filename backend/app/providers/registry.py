from __future__ import annotations

from app.core.config import settings
from app.providers.base import LLMProvider, SegmentProvider, TTSProvider
from app.providers.constants import (
    GENERATION_MODE_IMAGE,
    GENERATION_MODE_VIDEO,
    IMAGE_MINIMAX,
    LLM_MINIMAX,
    TTS_MINIMAX,
    VIDEO_MINIMAX_HAILUO,
)
from app.providers.llm.minimax import minimax_llm_provider
from app.providers.segment.image.minimax import minimax_image_provider
from app.providers.segment.video.minimax import minimax_hailuo_provider
from app.providers.tts.minimax import minimax_tts_provider

_LLM: dict[str, LLMProvider] = {
    LLM_MINIMAX: minimax_llm_provider,
}

_TTS: dict[str, TTSProvider] = {
    TTS_MINIMAX: minimax_tts_provider,
}

_SEGMENT: dict[str, SegmentProvider] = {
    IMAGE_MINIMAX: minimax_image_provider,
    VIDEO_MINIMAX_HAILUO: minimax_hailuo_provider,
}


def _parse_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def enabled_llm_providers() -> list[str]:
    raw = getattr(settings, "enabled_llm_providers", None) or LLM_MINIMAX
    return _parse_csv(raw)


def enabled_tts_providers() -> list[str]:
    raw = getattr(settings, "enabled_tts_providers", None) or TTS_MINIMAX
    return _parse_csv(raw)


def enabled_image_providers() -> list[str]:
    raw = getattr(settings, "enabled_image_providers", None) or IMAGE_MINIMAX
    return _parse_csv(raw)


def enabled_video_providers() -> list[str]:
    raw = getattr(settings, "enabled_video_providers", None) or VIDEO_MINIMAX_HAILUO
    return _parse_csv(raw)


def get_llm_provider(provider_id: str) -> LLMProvider:
    if provider_id not in _LLM:
        raise KeyError(f"Unknown LLM provider: {provider_id}")
    return _LLM[provider_id]


def get_tts_provider(provider_id: str) -> TTSProvider:
    if provider_id not in _TTS:
        raise KeyError(f"Unknown TTS provider: {provider_id}")
    return _TTS[provider_id]


def get_segment_provider(provider_id: str) -> SegmentProvider:
    if provider_id not in _SEGMENT:
        raise KeyError(f"Unknown segment provider: {provider_id}")
    return _SEGMENT[provider_id]


def list_segment_providers(mode: str) -> list[SegmentProvider]:
    target = GENERATION_MODE_VIDEO if mode == GENERATION_MODE_VIDEO else GENERATION_MODE_IMAGE
    enabled = enabled_video_providers() if target == GENERATION_MODE_VIDEO else enabled_image_providers()
    return [get_segment_provider(pid) for pid in enabled if pid in _SEGMENT and _SEGMENT[pid].generation_mode == target]


def default_segment_provider(generation_mode: str) -> str:
    if generation_mode == GENERATION_MODE_VIDEO:
        providers = enabled_video_providers()
        return providers[0] if providers else VIDEO_MINIMAX_HAILUO
    providers = enabled_image_providers()
    return providers[0] if providers else IMAGE_MINIMAX


def is_provider_configured(provider_id: str) -> bool:
    if provider_id in (LLM_MINIMAX, TTS_MINIMAX, IMAGE_MINIMAX, VIDEO_MINIMAX_HAILUO):
        return bool(settings.minimax_api_key)
    return False
