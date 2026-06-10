from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import FinalOutput, StoryboardSegment, VideoTask
from app.schemas.task import CreateTaskRequest, FinalOutputResponse, SegmentResponse, TaskResponse
from app.services.storage_service import storage_service
from app.workers.tasks import run_pipeline


def build_task_response(task: VideoTask) -> TaskResponse:
    segments = []
    for seg in sorted(task.segments, key=lambda s: s.segment_index):
        video_url = None
        if seg.video_path:
            video_url = storage_service.to_public_url(storage_service.base_path / seg.video_path)
        segments.append(SegmentResponse(
            id=seg.id,
            segment_index=seg.segment_index,
            status=seg.status,
            narration_text=seg.narration_text,
            subtitle_text=seg.subtitle_text,
            visual_description=seg.visual_description,
            camera_movement=seg.camera_movement,
            video_url=video_url,
            error_message=seg.error_message,
        ))

    output = None
    if task.output:
        output = FinalOutputResponse(
            video_url=storage_service.to_public_url(
                storage_service.base_path / task.output.video_path
            ),
            duration_ms=task.output.duration_ms,
            file_size_bytes=task.output.file_size_bytes,
        )

    return TaskResponse(
        id=task.id,
        status=task.status,
        progress=task.progress,
        progress_message=task.progress_message,
        input_config=task.input_config,
        total_segments=task.total_segments,
        segment_duration_sec=task.segment_duration_sec,
        error_message=task.error_message,
        created_at=task.created_at,
        completed_at=task.completed_at,
        segments=segments,
        output=output,
    )


async def create_task(db: AsyncSession, req: CreateTaskRequest) -> VideoTask:
    input_config = {
        "prompt": req.prompt,
        "theme": req.theme,
        "style": req.style,
        "audience": req.audience,
        "script_direction": req.script_direction,
        "bgm_enabled": req.bgm_enabled,
        "segment_count": settings.segment_count,
        "segment_duration_sec": settings.segment_duration_sec,
    }
    task = VideoTask(
        session_id=req.session_id,
        input_config=input_config,
        total_segments=settings.segment_count,
        segment_duration_sec=settings.segment_duration_sec,
        progress_message="已提交任务",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    from app.utils.progress import publish_progress

    publish_progress(str(task.id), "pending", "pending", 0, "已提交任务")

    run_pipeline.delay(str(task.id))
    return task


async def get_task(db: AsyncSession, task_id: UUID) -> VideoTask | None:
    result = await db.execute(
        select(VideoTask)
        .options(
            selectinload(VideoTask.segments),
            selectinload(VideoTask.output),
        )
        .where(VideoTask.id == task_id)
    )
    return result.scalar_one_or_none()


async def list_tasks(db: AsyncSession, session_id: str | None = None, limit: int = 20) -> tuple[list[VideoTask], int]:
    query = select(VideoTask).options(
        selectinload(VideoTask.segments),
        selectinload(VideoTask.output),
    )
    count_query = select(func.count()).select_from(VideoTask)

    if session_id:
        query = query.where(VideoTask.session_id == session_id)
        count_query = count_query.where(VideoTask.session_id == session_id)

    query = query.order_by(VideoTask.created_at.desc()).limit(limit)
    result = await db.execute(query)
    tasks = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    return tasks, total
