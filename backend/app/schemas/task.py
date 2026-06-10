from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    SCRIPT_GENERATING = "script_generating"
    STORYBOARD_GENERATING = "storyboard_generating"
    SEGMENT_GENERATING = "segment_generating"
    VOICEOVER_GENERATING = "voiceover_generating"
    COMPOSING = "composing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CreateTaskRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=5000, description="视频创作方案描述")
    theme: str | None = Field(None, max_length=200)
    style: str | None = Field(None, max_length=200)
    audience: str | None = Field(None, max_length=200)
    script_direction: str | None = Field(None, max_length=1000)
    session_id: str | None = Field(None, max_length=64)
    bgm_enabled: bool = False


class SegmentResponse(BaseModel):
    id: UUID
    segment_index: int
    status: str
    narration_text: str | None = None
    subtitle_text: str | None = None
    visual_description: str | None = None
    camera_movement: str | None = None
    video_url: str | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}


class FinalOutputResponse(BaseModel):
    video_url: str
    duration_ms: int | None = None
    file_size_bytes: int | None = None

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    id: UUID
    status: str
    progress: int
    progress_message: str | None
    input_config: dict
    total_segments: int
    segment_duration_sec: int
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    segments: list[SegmentResponse] = []
    output: FinalOutputResponse | None = None

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int


class ProgressEvent(BaseModel):
    task_id: str
    status: str
    stage: str
    progress: int
    message: str
    current_segment: int | None = None
    total_segments: int | None = None
    timestamp: str
