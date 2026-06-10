import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    SCRIPT_GENERATING = "script_generating"
    STORYBOARD_GENERATING = "storyboard_generating"
    SEGMENT_GENERATING = "segment_generating"
    VOICEOVER_GENERATING = "voiceover_generating"
    COMPOSING = "composing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SegmentStatus(str, enum.Enum):
    PENDING = "pending"
    VIDEO_GENERATING = "video_generating"
    VIDEO_READY = "video_ready"
    FAILED = "failed"


class VideoTask(Base):
    __tablename__ = "video_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default=TaskStatus.PENDING.value, index=True)
    input_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    script_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    total_segments: Mapped[int] = mapped_column(Integer, default=30)
    segment_duration_sec: Mapped[int] = mapped_column(Integer, default=6)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    progress_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    segments: Mapped[list["StoryboardSegment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", order_by="StoryboardSegment.segment_index"
    )
    output: Mapped["FinalOutput | None"] = relationship(back_populates="task", uselist=False)
    events: Mapped[list["TaskEvent"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", order_by="TaskEvent.created_at"
    )


class StoryboardSegment(Base):
    __tablename__ = "storyboard_segments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("video_tasks.id"), index=True)
    segment_index: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default=SegmentStatus.PENDING.value)
    scene_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    narration_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    subtitle_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    camera_movement: Mapped[str | None] = mapped_column(Text, nullable=True)
    minimax_task_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    video_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_frame_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    task: Mapped["VideoTask"] = relationship(back_populates="segments")


class FinalOutput(Base):
    __tablename__ = "final_outputs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("video_tasks.id"), unique=True)
    video_path: Mapped[str] = mapped_column(String(512))
    audio_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    subtitle_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    task: Mapped["VideoTask"] = relationship(back_populates="output")


class TaskEvent(Base):
    __tablename__ = "task_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("video_tasks.id"), index=True)
    stage: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(String(512))
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped["VideoTask"] = relationship(back_populates="events")
