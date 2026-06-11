from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.providers.constants import (
    GENERATION_MODE_IMAGE,
    GENERATION_MODE_VIDEO,
    LLM_MINIMAX,
    TTS_MINIMAX,
)
from app.providers.registry import (
    default_segment_provider,
    get_segment_provider,
    is_provider_configured,
)


@dataclass(frozen=True)
class ResolvedTaskProviders:
    generation_mode: str
    llm_provider: str
    tts_provider: str
    segment_provider: str
    segment_duration_sec: int
    provider_snapshot: dict[str, Any]

    @property
    def is_image_mode(self) -> bool:
        return self.generation_mode != GENERATION_MODE_VIDEO

    @property
    def prompt_profile(self) -> str:
        """LLM prompt template follows segment provider."""
        return self.segment_provider


def resolve_generation_mode(input_config: dict | None) -> str:
    cfg = input_config or {}
    mode = (cfg.get("generation_mode") or settings.generation_mode or GENERATION_MODE_IMAGE).strip().lower()
    return GENERATION_MODE_VIDEO if mode == GENERATION_MODE_VIDEO else GENERATION_MODE_IMAGE


def resolve_task_providers(
    input_config: dict | None,
    segment_duration_sec: int | None = None,
) -> ResolvedTaskProviders:
    """Resolve providers from task input_config with env fallbacks for legacy tasks."""
    cfg = input_config or {}
    generation_mode = resolve_generation_mode(cfg)

    llm_provider = cfg.get("llm_provider") or getattr(settings, "default_llm_provider", None) or LLM_MINIMAX
    tts_provider = cfg.get("tts_provider") or getattr(settings, "default_tts_provider", None) or TTS_MINIMAX
    segment_provider = cfg.get("segment_provider") or default_segment_provider(generation_mode)

    duration = segment_duration_sec
    if duration is None:
        duration = int(cfg.get("segment_duration_sec") or settings.segment_duration_sec)

    segment = get_segment_provider(segment_provider)
    caps = segment.capabilities()

    snapshot = cfg.get("provider_snapshot") or {
        "generation_mode": generation_mode,
        "llm_provider": llm_provider,
        "tts_provider": tts_provider,
        "segment_provider": segment_provider,
        "segment": {
            "display_name": caps.display_name,
            "supports_first_frame": caps.supports_first_frame,
            "hard_cut_between_segments": caps.hard_cut_between_segments,
            "max_duration_sec": caps.max_duration_sec,
        },
    }

    return ResolvedTaskProviders(
        generation_mode=generation_mode,
        llm_provider=llm_provider,
        tts_provider=tts_provider,
        segment_provider=segment_provider,
        segment_duration_sec=duration,
        provider_snapshot=snapshot,
    )


def build_provider_snapshot(
    generation_mode: str,
    llm_provider: str,
    tts_provider: str,
    segment_provider: str,
) -> dict[str, Any]:
    from app.providers.registry import get_llm_provider, get_tts_provider

    segment = get_segment_provider(segment_provider)
    caps = segment.capabilities()
    llm_caps = get_llm_provider(llm_provider).capabilities()
    tts_caps = get_tts_provider(tts_provider).capabilities()
    return {
        "generation_mode": generation_mode,
        "llm_provider": llm_provider,
        "tts_provider": tts_provider,
        "segment_provider": segment_provider,
        "segment": {
            "display_name": caps.display_name,
            "supports_first_frame": caps.supports_first_frame,
            "hard_cut_between_segments": caps.hard_cut_between_segments,
            "max_duration_sec": caps.max_duration_sec,
            "allowed_durations": caps.allowed_durations,
        },
        "llm": {"display_name": llm_caps.display_name},
        "tts": {"display_name": tts_caps.display_name},
    }


def provider_enabled(provider_id: str, enabled_list: list[str]) -> bool:
    return provider_id in enabled_list and is_provider_configured(provider_id)
