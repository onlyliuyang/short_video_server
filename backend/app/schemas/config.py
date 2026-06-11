from pydantic import BaseModel


class ProviderCapabilitiesResponse(BaseModel):
    max_duration_sec: int
    allowed_durations: list[int] = []
    supported_resolutions: list[str] = []
    supported_aspect_ratios: list[str] = []
    supports_first_frame: bool = False
    supports_last_frame: bool = False
    hard_cut_between_segments: bool = False
    default_concurrency: int = 3
    estimated_cost_hint: str | None = None


class ProviderOptionResponse(BaseModel):
    id: str
    label: str
    enabled: bool
    disabled_reason: str | None = None
    capabilities: ProviderCapabilitiesResponse | None = None


class GenerationModeOption(BaseModel):
    id: str
    label: str
    description: str


class ProviderDefaultsResponse(BaseModel):
    generation_mode: str
    llm_provider: str
    tts_provider: str
    segment_provider: str


class ProvidersConfigResponse(BaseModel):
    defaults: ProviderDefaultsResponse
    generation_modes: list[GenerationModeOption]
    llm_providers: list[ProviderOptionResponse]
    tts_providers: list[ProviderOptionResponse]
    segment_providers: dict[str, list[ProviderOptionResponse]]


class VideoConfigResponse(BaseModel):
    segment_count: int
    segment_duration_sec: int
    total_duration_sec: int
    segment_transition_sec: float
    generation_mode: str
    video_resolution: str
    video_concurrency: int
    image_aspect_ratio: str
