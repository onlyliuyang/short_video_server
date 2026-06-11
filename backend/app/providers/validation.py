from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.providers.constants import GENERATION_MODE_IMAGE, GENERATION_MODE_VIDEO
from app.providers.registry import (
    default_segment_provider,
    enabled_image_providers,
    enabled_llm_providers,
    enabled_tts_providers,
    enabled_video_providers,
    get_llm_provider,
    get_segment_provider,
    get_tts_provider,
    is_provider_configured,
)
from app.providers.task_config import build_provider_snapshot, resolve_generation_mode


@dataclass
class ValidationErrorDetail:
    code: str
    message: str
    provider: str | None = None
    max_duration_sec: int | None = None
    allowed_durations: list[int] | None = None


class TaskProviderValidationError(ValueError):
    def __init__(self, detail: ValidationErrorDetail):
        self.detail = detail
        super().__init__(detail.message)


def validate_task_providers(
    *,
    generation_mode: str | None = None,
    llm_provider: str | None = None,
    tts_provider: str | None = None,
    segment_provider: str | None = None,
    segment_duration_sec: int | None = None,
) -> dict:
    """Validate and normalize provider selection. Returns normalized input_config fields."""

    mode = (generation_mode or settings.generation_mode or GENERATION_MODE_IMAGE).strip().lower()
    mode = GENERATION_MODE_VIDEO if mode == GENERATION_MODE_VIDEO else GENERATION_MODE_IMAGE

    llm_id = llm_provider or getattr(settings, "default_llm_provider", None) or "minimax_llm"
    tts_id = tts_provider or getattr(settings, "default_tts_provider", None) or "minimax_tts"
    seg_id = segment_provider or default_segment_provider(mode)
    duration = segment_duration_sec if segment_duration_sec is not None else settings.segment_duration_sec

    if llm_id not in enabled_llm_providers():
        raise TaskProviderValidationError(ValidationErrorDetail(
            code="LLM_PROVIDER_DISABLED",
            message=f"LLM provider '{llm_id}' 未启用",
            provider=llm_id,
        ))
    if tts_id not in enabled_tts_providers():
        raise TaskProviderValidationError(ValidationErrorDetail(
            code="TTS_PROVIDER_DISABLED",
            message=f"TTS provider '{tts_id}' 未启用",
            provider=tts_id,
        ))

    enabled_segments = enabled_video_providers() if mode == GENERATION_MODE_VIDEO else enabled_image_providers()
    if seg_id not in enabled_segments:
        raise TaskProviderValidationError(ValidationErrorDetail(
            code="SEGMENT_PROVIDER_DISABLED",
            message=f"分段 provider '{seg_id}' 未启用",
            provider=seg_id,
        ))

    if not is_provider_configured(llm_id):
        raise TaskProviderValidationError(ValidationErrorDetail(
            code="LLM_NOT_CONFIGURED",
            message=f"LLM provider '{llm_id}' 未配置 API Key",
            provider=llm_id,
        ))
    if not is_provider_configured(tts_id):
        raise TaskProviderValidationError(ValidationErrorDetail(
            code="TTS_NOT_CONFIGURED",
            message=f"TTS provider '{tts_id}' 未配置 API Key",
            provider=tts_id,
        ))
    if not is_provider_configured(seg_id):
        raise TaskProviderValidationError(ValidationErrorDetail(
            code="SEGMENT_NOT_CONFIGURED",
            message=f"分段 provider '{seg_id}' 未配置 API Key",
            provider=seg_id,
        ))

    segment = get_segment_provider(seg_id)
    caps = segment.capabilities()

    if caps.generation_mode != mode:
        raise TaskProviderValidationError(ValidationErrorDetail(
            code="MODE_PROVIDER_MISMATCH",
            message=f"生成模式 '{mode}' 与 provider '{seg_id}' 不匹配",
            provider=seg_id,
        ))

    if duration > caps.max_duration_sec:
        raise TaskProviderValidationError(ValidationErrorDetail(
            code="INVALID_SEGMENT_DURATION",
            message=f"{caps.display_name} 单段最长支持 {caps.max_duration_sec} 秒，当前 segment_duration_sec={duration}",
            provider=seg_id,
            max_duration_sec=caps.max_duration_sec,
            allowed_durations=caps.allowed_durations or None,
        ))

    if caps.allowed_durations and duration not in caps.allowed_durations:
        raise TaskProviderValidationError(ValidationErrorDetail(
            code="INVALID_SEGMENT_DURATION",
            message=f"{caps.display_name} 仅支持时长 {caps.allowed_durations} 秒，当前 segment_duration_sec={duration}",
            provider=seg_id,
            max_duration_sec=caps.max_duration_sec,
            allowed_durations=caps.allowed_durations,
        ))

    # Touch providers to ensure registration
    get_llm_provider(llm_id)
    get_tts_provider(tts_id)

    snapshot = build_provider_snapshot(mode, llm_id, tts_id, seg_id)

    return {
        "generation_mode": mode,
        "llm_provider": llm_id,
        "tts_provider": tts_id,
        "segment_provider": seg_id,
        "segment_duration_sec": duration,
        "provider_snapshot": snapshot,
    }
