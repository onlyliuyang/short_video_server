"""Unified segment generation worker."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import SegmentStatus, StoryboardSegment, TaskStatus, VideoTask
from app.providers.base import CreateSegmentJobRequest, SegmentPromptContext
from app.providers.constants import GENERATION_MODE_IMAGE
from app.providers.errors import is_non_retryable, user_facing_message
from app.providers.registry import get_segment_provider
from app.providers.task_config import resolve_task_providers
from app.services.ffmpeg_service import ffmpeg_service
from app.services.storage_service import storage_service
from app.utils.progress import publish_progress

logger = logging.getLogger(__name__)


def _update_task_message(db: Session, task_id: str, progress: int, message: str) -> None:
    db.query(VideoTask).filter(VideoTask.id == uuid.UUID(task_id)).update(
        {"progress": progress, "progress_message": message}
    )
    db.commit()


def _get_segment(db: Session, task_id: str, segment_index: int) -> StoryboardSegment:
    return (
        db.query(StoryboardSegment)
        .filter(
            StoryboardSegment.task_id == uuid.UUID(task_id),
            StoryboardSegment.segment_index == segment_index,
        )
        .one()
    )


def _mark_segment_ready_video(
    db: Session,
    task_id: str,
    segment_index: int,
    video_path: Path,
    last_frame_path: Path,
    provider_job_id: str | None = None,
) -> None:
    updates: dict = {
        "status": SegmentStatus.VIDEO_READY.value,
        "video_path": storage_service.to_relative_path(video_path),
        "last_frame_path": storage_service.to_relative_path(last_frame_path),
        "error_message": None,
    }
    if provider_job_id:
        updates["minimax_task_id"] = provider_job_id
    db.query(StoryboardSegment).filter(
        StoryboardSegment.task_id == uuid.UUID(task_id),
        StoryboardSegment.segment_index == segment_index,
    ).update(updates)
    db.commit()


def _mark_segment_ready_image(
    db: Session,
    task_id: str,
    segment_index: int,
    image_path: Path,
    video_path: Path,
) -> None:
    db.query(StoryboardSegment).filter(
        StoryboardSegment.task_id == uuid.UUID(task_id),
        StoryboardSegment.segment_index == segment_index,
    ).update(
        {
            "status": SegmentStatus.VIDEO_READY.value,
            "video_path": storage_service.to_relative_path(video_path),
            "last_frame_path": storage_service.to_relative_path(image_path),
            "error_message": None,
        }
    )
    db.commit()


def _mark_segment_failed(db: Session, task_id: str, segment_index: int, error: str, retry_count: int) -> None:
    db.rollback()
    db.query(StoryboardSegment).filter(
        StoryboardSegment.task_id == uuid.UUID(task_id),
        StoryboardSegment.segment_index == segment_index,
    ).update(
        {
            "status": SegmentStatus.FAILED.value,
            "error_message": error,
            "retry_count": retry_count,
        }
    )
    db.commit()


def _publish_sub(
    db: Session,
    task_id: str,
    total: int,
    segment_index: int,
    message: str,
    progress: int,
    stage: str,
) -> None:
    publish_progress(
        task_id,
        TaskStatus.SEGMENT_GENERATING.value,
        stage,
        progress,
        message,
        current_segment=segment_index,
        total_segments=total,
    )
    _update_task_message(db, task_id, progress, message)


def _resolve_first_frame(
    task_id: str,
    segment_index: int,
    supports_first_frame: bool,
) -> Path | None:
    if segment_index <= 1:
        return None
    prev_frame = storage_service.segment_frame_path(task_id, segment_index - 1, "last")
    if not prev_frame.exists():
        return None
    if not supports_first_frame:
        logger.debug("Provider does not support first_frame; segment %d will hard-cut", segment_index)
    return prev_frame


def generate_single_segment(db: Session, task_id: str, segment_index: int, max_retries: int = 3) -> None:
    task = db.query(VideoTask).filter(VideoTask.id == uuid.UUID(task_id)).one()
    resolved = resolve_task_providers(task.input_config, task.segment_duration_sec)
    provider = get_segment_provider(resolved.segment_provider)
    caps = provider.capabilities()
    display_name = caps.display_name
    is_image = resolved.generation_mode == GENERATION_MODE_IMAGE
    stage = "segment_image" if is_image else "segment_video"

    segment = _get_segment(db, task_id, segment_index)
    global_style = (task.script_json or {}).get("global_style", "")
    setting_anchor = (task.script_json or {}).get("setting_anchor", "")
    setting_keywords = (task.script_json or {}).get("setting_keywords") or []
    user_prompt = (task.input_config or {}).get("prompt", "")
    segments_data = (task.script_json or {}).get("segments", [])
    seg_data = next((s for s in segments_data if s.get("index") == segment_index), {})

    image_path = storage_service.segment_image_path(task_id, segment_index)
    video_path = storage_service.segment_video_path(task_id, segment_index)
    last_frame_path = storage_service.segment_frame_path(task_id, segment_index, "last")
    holder_id = f"{task_id}:{segment_index}"

    if segment.status == SegmentStatus.VIDEO_READY.value and video_path.exists():
        if is_image and image_path.exists():
            logger.info("Segment %d already ready, skip", segment_index)
            return
        if not is_image and last_frame_path.exists():
            logger.info("Segment %d already ready, skip", segment_index)
            return

    if not is_image and video_path.exists() and not last_frame_path.exists():
        logger.info("Segment %d video exists, resume extract last frame", segment_index)
        _publish_sub(
            db, task_id, task.total_segments, segment_index,
            f"正在提取第 {segment_index}/{task.total_segments} 个片段末帧...",
            15, stage,
        )
        ffmpeg_service.extract_last_frame(video_path, last_frame_path)
        _mark_segment_ready_video(db, task_id, segment_index, video_path, last_frame_path)
        return

    if is_image and video_path.exists() and not image_path.exists():
        logger.info("Segment %d clip exists, skip image regen", segment_index)
        return

    prev_end_visual = ""
    if segment_index > 1:
        prev_segments = [s for s in segments_data if s.get("index") == segment_index - 1]
        if prev_segments:
            prev_end_visual = prev_segments[0].get("end_visual_description", "")

    prompt_ctx = SegmentPromptContext(
        segment_index=segment_index,
        scene_prompt=segment.scene_prompt or "",
        visual_description=segment.visual_description or "",
        camera_movement=segment.camera_movement or "",
        global_style=global_style,
        seg_data=seg_data,
        setting_anchor=setting_anchor,
        user_prompt=str(user_prompt),
        setting_keywords=setting_keywords,
        prev_end_visual=prev_end_visual,
    )
    prompt = provider.build_prompt(prompt_ctx)

    first_frame = _resolve_first_frame(task_id, segment_index, caps.supports_first_frame)
    motion_hint = seg_data.get("motion_hint") or seg_data.get("camera_movement") or segment.camera_movement or ""

    db.query(StoryboardSegment).filter(
        StoryboardSegment.task_id == uuid.UUID(task_id),
        StoryboardSegment.segment_index == segment_index,
    ).update({"status": SegmentStatus.VIDEO_GENERATING.value})
    db.commit()

    total = task.total_segments
    base_progress = 15 + int(((segment_index - 1) / total) * 55)
    segment_span = max(1, int(55 / total))

    logger.info(
        "Segment %d/%d provider=%s prompt_len=%d first_frame=%s",
        segment_index, total, resolved.segment_provider, len(prompt), first_frame,
    )
    logger.info("[%s] segment=%d prompt: %s", display_name, segment_index, prompt[:500])

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            job_req = CreateSegmentJobRequest(
                prompt=prompt,
                duration_sec=task.segment_duration_sec,
                first_frame_path=first_frame,
                last_frame_path=None,
                holder_id=holder_id,
                motion_hint=motion_hint,
                camera_movement=segment.camera_movement or "",
            )

            if is_image:
                if not image_path.exists():
                    _publish_sub(
                        db, task_id, total, segment_index,
                        f"正在生成第 {segment_index}/{total} 张分镜图 ({display_name})...",
                        base_progress, stage,
                    )
                    download_ref = provider.create_job(job_req)
                    provider.poll_and_download(download_ref, image_path, holder_id=holder_id)

                _publish_sub(
                    db, task_id, total, segment_index,
                    f"正在渲染第 {segment_index}/{total} 个视频片段...",
                    min(70, base_progress + segment_span // 2), stage,
                )
                ffmpeg_service.image_to_clip(
                    image_path,
                    video_path,
                    duration_sec=float(task.segment_duration_sec),
                    motion_hint=motion_hint,
                    camera_movement=segment.camera_movement or "",
                )
                _mark_segment_ready_image(db, task_id, segment_index, image_path, video_path)
                logger.info("Segment %d/%d image mode done -> %s", segment_index, total, video_path)
                return

            _publish_sub(
                db, task_id, total, segment_index,
                f"正在提交第 {segment_index}/{total} 个片段到 {display_name}...",
                base_progress, stage,
            )
            provider_job_id = provider.create_job(job_req)

            db.query(StoryboardSegment).filter(
                StoryboardSegment.task_id == uuid.UUID(task_id),
                StoryboardSegment.segment_index == segment_index,
            ).update({"minimax_task_id": provider_job_id})
            db.commit()

            def on_poll(poll_attempt: int, status: str, _data: dict) -> None:
                if poll_attempt == 1 or poll_attempt % 3 == 0:
                    _publish_sub(
                        db, task_id, total, segment_index,
                        f"第 {segment_index}/{total} 个片段 {display_name} 状态: {status or '等待中'} (轮询 #{poll_attempt})",
                        min(70, base_progress + min(segment_span - 1, poll_attempt // 2)),
                        stage,
                    )

            _publish_sub(
                db, task_id, total, segment_index,
                f"正在等待 {display_name} 生成第 {segment_index}/{total} 个片段...",
                base_progress, stage,
            )
            provider.poll_and_download(
                provider_job_id, video_path, holder_id=holder_id, on_poll=on_poll,
            )

            _publish_sub(
                db, task_id, total, segment_index,
                f"正在提取第 {segment_index}/{total} 个片段末帧...",
                base_progress + 1, stage,
            )
            ffmpeg_service.extract_last_frame(video_path, last_frame_path)
            _mark_segment_ready_video(
                db, task_id, segment_index, video_path, last_frame_path, provider_job_id,
            )
            logger.info("Segment %d/%d done -> %s", segment_index, total, video_path)
            return

        except Exception as e:
            last_error = e
            logger.exception("Segment %d attempt %d failed: %s", segment_index, attempt, e)
            _mark_segment_failed(db, task_id, segment_index, str(e), attempt)
            if is_non_retryable(e):
                break
            if is_image and image_path.exists():
                image_path.unlink(missing_ok=True)

    raise RuntimeError(
        user_facing_message(last_error) if last_error else
        f"Segment {segment_index} failed after {max_retries} retries"
    )


# Backward-compatible aliases
generate_single_segment_image = generate_single_segment
generate_single_segment_video = generate_single_segment
