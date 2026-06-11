from fastapi import APIRouter

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
from app.schemas.config import (
    GenerationModeOption,
    ProviderCapabilitiesResponse,
    ProviderDefaultsResponse,
    ProviderOptionResponse,
    ProvidersConfigResponse,
    VideoConfigResponse,
)

router = APIRouter(prefix="/config", tags=["config"])


def _segment_option(provider_id: str) -> ProviderOptionResponse:
    provider = get_segment_provider(provider_id)
    caps = provider.capabilities()
    configured = is_provider_configured(provider_id)
    return ProviderOptionResponse(
        id=provider_id,
        label=caps.display_name,
        enabled=configured,
        disabled_reason=None if configured else "未配置 API Key",
        capabilities=ProviderCapabilitiesResponse(
            max_duration_sec=caps.max_duration_sec,
            allowed_durations=caps.allowed_durations,
            supported_resolutions=caps.supported_resolutions,
            supported_aspect_ratios=caps.supported_aspect_ratios,
            supports_first_frame=caps.supports_first_frame,
            supports_last_frame=caps.supports_last_frame,
            hard_cut_between_segments=caps.hard_cut_between_segments,
            default_concurrency=caps.default_concurrency,
            estimated_cost_hint=caps.estimated_cost_hint,
        ),
    )


@router.get("/video", response_model=VideoConfigResponse)
async def get_video_config():
    return VideoConfigResponse(
        segment_count=settings.segment_count,
        segment_duration_sec=settings.segment_duration_sec,
        total_duration_sec=settings.effective_total_duration_sec,
        segment_transition_sec=settings.segment_transition_sec,
        generation_mode=settings.generation_mode,
        video_resolution=settings.video_resolution,
        video_concurrency=settings.video_concurrency,
        image_aspect_ratio=settings.image_aspect_ratio,
    )


@router.get("/providers", response_model=ProvidersConfigResponse)
async def get_providers_config():
    default_mode = settings.default_generation_mode or settings.generation_mode
    default_seg = default_segment_provider(default_mode)

    llm_options = []
    for pid in enabled_llm_providers():
        p = get_llm_provider(pid)
        caps = p.capabilities()
        configured = is_provider_configured(pid)
        llm_options.append(ProviderOptionResponse(
            id=pid,
            label=caps.display_name,
            enabled=configured,
            disabled_reason=None if configured else "未配置 API Key",
        ))

    tts_options = []
    for pid in enabled_tts_providers():
        p = get_tts_provider(pid)
        caps = p.capabilities()
        configured = is_provider_configured(pid)
        tts_options.append(ProviderOptionResponse(
            id=pid,
            label=caps.display_name,
            enabled=configured,
            disabled_reason=None if configured else "未配置 API Key",
        ))

    image_options = [_segment_option(pid) for pid in enabled_image_providers() if pid in enabled_image_providers()]
    video_options = [_segment_option(pid) for pid in enabled_video_providers() if pid in enabled_video_providers()]

    return ProvidersConfigResponse(
        defaults=ProviderDefaultsResponse(
            generation_mode=default_mode,
            llm_provider=settings.default_llm_provider,
            tts_provider=settings.default_tts_provider,
            segment_provider=default_seg,
        ),
        generation_modes=[
            GenerationModeOption(
                id=GENERATION_MODE_IMAGE,
                label="图片模式",
                description="文生图 + Ken Burns 动效，成本较低",
            ),
            GenerationModeOption(
                id=GENERATION_MODE_VIDEO,
                label="视频模式",
                description="AI 直出视频片段，质量更高",
            ),
        ],
        llm_providers=llm_options,
        tts_providers=tts_options,
        segment_providers={
            GENERATION_MODE_IMAGE: image_options,
            GENERATION_MODE_VIDEO: video_options,
        },
    )
