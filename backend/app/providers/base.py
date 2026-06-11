from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Protocol


@dataclass(frozen=True)
class SegmentProviderCapabilities:
    provider_id: str
    display_name: str
    generation_mode: Literal["image", "video"]
    max_duration_sec: int
    allowed_durations: list[int] = field(default_factory=list)
    supported_resolutions: list[str] = field(default_factory=list)
    supported_aspect_ratios: list[str] = field(default_factory=list)
    supports_first_frame: bool = False
    supports_last_frame: bool = False
    default_concurrency: int = 3
    estimated_cost_hint: str | None = None

    @property
    def hard_cut_between_segments(self) -> bool:
        return not self.supports_first_frame


@dataclass(frozen=True)
class LLMProviderCapabilities:
    provider_id: str
    display_name: str
    max_output_tokens: int = 16384
    supports_json_mode: bool = False


@dataclass(frozen=True)
class TTSProviderCapabilities:
    provider_id: str
    display_name: str
    supported_languages: list[str] = field(default_factory=lambda: ["zh"])
    max_chars_per_request: int = 5000
    default_voice_id: str = ""
    supports_timeline_mix: bool = True


@dataclass
class StoryboardRequest:
    prompt: str
    theme: str | None
    style: str | None
    audience: str | None
    script_direction: str | None
    segment_count: int
    segment_duration_sec: int
    generation_mode: str
    prompt_profile: str  # segment provider id for prompt template selection


@dataclass
class SegmentPromptContext:
    segment_index: int
    scene_prompt: str
    visual_description: str
    camera_movement: str
    global_style: str
    seg_data: dict[str, Any]
    setting_anchor: str
    user_prompt: str
    setting_keywords: list[str]
    prev_end_visual: str = ""


@dataclass
class CreateSegmentJobRequest:
    prompt: str
    duration_sec: int
    first_frame_path: Path | None
    last_frame_path: Path | None
    holder_id: str
    motion_hint: str = ""
    camera_movement: str = ""


PollCallback = Callable[[int, str, dict], None]


class LLMProvider(Protocol):
    provider_id: str

    def capabilities(self) -> LLMProviderCapabilities: ...

    def generate_storyboard(self, req: StoryboardRequest) -> dict: ...


class TTSProvider(Protocol):
    provider_id: str

    def capabilities(self) -> TTSProviderCapabilities: ...

    def synthesize(self, text: str, output_path: Path, voice_id: str | None = None) -> None: ...


class SegmentProvider(Protocol):
    provider_id: str
    generation_mode: Literal["image", "video"]

    def capabilities(self) -> SegmentProviderCapabilities: ...

    def build_prompt(self, ctx: SegmentPromptContext) -> str: ...

    def create_job(self, req: CreateSegmentJobRequest) -> str: ...

    def poll_and_download(
        self,
        job_id: str,
        output_path: Path,
        *,
        holder_id: str,
        on_poll: PollCallback | None = None,
    ) -> None: ...
