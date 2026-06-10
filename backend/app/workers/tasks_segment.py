import logging
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import SegmentStatus, StoryboardSegment, TaskStatus, VideoTask
from app.services.ffmpeg_service import ffmpeg_service
from app.services.minimax_video import video_service
from app.services.storage_service import storage_service
from app.utils.progress import publish_progress

logger = logging.getLogger(__name__)


def _build_video_prompt(
    segment: StoryboardSegment,
    global_style: str,
    seg_data: dict,
    segment_index: int,
    setting_anchor: str = "",
    user_prompt: str = "",
    setting_keywords: list[str] | None = None,
    prev_end_visual: str = "",
) -> str:
    """Assemble MiniMax video prompt with motion, shot variety, setting lock, and continuity."""
    parts: list[str] = []

    if setting_anchor:
        parts.append(f"MUST take place in this exact setting (never change location): {setting_anchor}")
    elif user_prompt:
        parts.append(f"MUST match user request setting: {user_prompt}")

    if setting_keywords:
        parts.append(f"Required visual elements: {', '.join(setting_keywords)}")

    if user_prompt:
        parts.append(f"User original request: {user_prompt}")

    scene = segment.scene_prompt or segment.visual_description or ""
    if scene:
        parts.append(scene)

    shot_type = seg_data.get("shot_type", "")
    if shot_type:
        parts.append(f"Shot type: {shot_type}")

    if segment_index == 1:
        start_visual = seg_data.get("start_visual_description", "")
        if start_visual:
            parts.append(f"Opening frame: {start_visual}")
    elif prev_end_visual:
        start_visual = seg_data.get("start_visual_description", "")
        continuity = start_visual or prev_end_visual
        parts.append(
            f"Continue from previous shot ending on: {prev_end_visual}. "
            f"New angle/focus: {continuity}. "
            f"Stay in the same setting: {setting_anchor or user_prompt}. "
            "Same world and lighting, but different framing — not a duplicate static frame."
        )

    motion = seg_data.get("motion_in_shot", "")
    if motion:
        parts.append(f"In-shot motion: {motion}")
    else:
        parts.append("Natural continuous motion throughout, no frozen still image")

    if segment.camera_movement:
        parts.append(f"Camera movement: {segment.camera_movement}")

    if global_style:
        parts.append(f"Visual style: {global_style}")

    end_visual = seg_data.get("end_visual_description", "")
    if end_visual:
        parts.append(f"End frame: {end_visual}")

    transition = seg_data.get("transition_to_next", "")
    if transition and segment_index > 0:
        parts.append(f"Transition hint: {transition}")

    parts.append(
        "Cinematic, photorealistic, dynamic clip with visible temporal progression. "
        "Do not change location or subject away from user request."
    )

    return ". ".join(p for p in parts if p)


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


def _mark_segment_ready(
    db: Session,
    task_id: str,
    segment_index: int,
    output_path: Path,
    last_frame_path: Path,
) -> None:
    db.query(StoryboardSegment).filter(
        StoryboardSegment.task_id == uuid.UUID(task_id),
        StoryboardSegment.segment_index == segment_index,
    ).update(
        {
            "status": SegmentStatus.VIDEO_READY.value,
            "video_path": storage_service.to_relative_path(output_path),
            "last_frame_path": storage_service.to_relative_path(last_frame_path),
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


def generate_single_segment(db: Session, task_id: str, segment_index: int, max_retries: int = 3) -> None:
    task = db.query(VideoTask).filter(VideoTask.id == uuid.UUID(task_id)).one()
    segment = _get_segment(db, task_id, segment_index)

    global_style = (task.script_json or {}).get("global_style", "")
    setting_anchor = (task.script_json or {}).get("setting_anchor", "")
    setting_keywords = (task.script_json or {}).get("setting_keywords") or []
    user_prompt = (task.input_config or {}).get("prompt", "")
    segments_data = (task.script_json or {}).get("segments", [])
    seg_data = next((s for s in segments_data if s.get("index") == segment_index), {})

    output_path = storage_service.segment_video_path(task_id, segment_index)
    last_frame_path = storage_service.segment_frame_path(task_id, segment_index, "last")
    holder_id = f"{task_id}:{segment_index}"

    # Resume: skip or only extract frame if video already downloaded
    if segment.status == SegmentStatus.VIDEO_READY.value and output_path.exists() and last_frame_path.exists():
        logger.info("Segment %d already ready, skip", segment_index)
        return
    if output_path.exists() and not last_frame_path.exists():
        logger.info("Segment %d video exists, resume extract last frame", segment_index)
        _publish_sub(db, task_id, task.total_segments, segment_index, f"正在提取第 {segment_index}/{task.total_segments} 个片段末帧...")
        ffmpeg_service.extract_last_frame(output_path, last_frame_path)
        _mark_segment_ready(db, task_id, segment_index, output_path, last_frame_path)
        return

    first_frame: Path | None = None
    prev_end_visual = ""
    if segment_index > 1:
        prev_frame = storage_service.segment_frame_path(task_id, segment_index - 1, "last")
        if prev_frame.exists():
            first_frame = prev_frame
        prev_segments = [s for s in segments_data if s.get("index") == segment_index - 1]
        if prev_segments:
            prev_end_visual = prev_segments[0].get("end_visual_description", "")

    prompt = _build_video_prompt(
        segment,
        global_style,
        seg_data,
        segment_index,
        setting_anchor=setting_anchor,
        user_prompt=str(user_prompt),
        setting_keywords=setting_keywords,
        prev_end_visual=prev_end_visual,
    )

    db.query(StoryboardSegment).filter(
        StoryboardSegment.task_id == uuid.UUID(task_id),
        StoryboardSegment.segment_index == segment_index,
    ).update({"status": SegmentStatus.VIDEO_GENERATING.value})
    db.commit()

    total = task.total_segments
    base_progress = 15 + int(((segment_index - 1) / total) * 55)
    segment_span = max(1, int(55 / total))

    logger.info(
        "Segment %d/%d start task=%s prompt_len=%d first_frame=%s",
        segment_index, total, task_id, len(prompt), first_frame,
    )
    logger.info("[MiniMax Video] segment=%d scene_prompt=%s", segment_index, segment.scene_prompt or "")
    logger.info("[MiniMax Video] segment=%d full prompt: %s", segment_index, prompt)

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            _publish_sub(db, task_id, total, segment_index, f"正在提交第 {segment_index}/{total} 个片段到 MiniMax...", base_progress)
            logger.info("Segment %d attempt %d/%d creating MiniMax task", segment_index, attempt, max_retries)

            minimax_task_id = video_service.create_video_task(
                prompt=prompt,
                duration=task.segment_duration_sec,
                first_frame_path=first_frame,
                holder_id=holder_id,
            )
            db.query(StoryboardSegment).filter(
                StoryboardSegment.task_id == uuid.UUID(task_id),
                StoryboardSegment.segment_index == segment_index,
            ).update({"minimax_task_id": minimax_task_id})
            db.commit()

            def on_poll(poll_attempt: int, status: str, _data: dict) -> None:
                if poll_attempt == 1 or poll_attempt % 3 == 0:
                    _publish_sub(
                        db, task_id, total, segment_index,
                        f"第 {segment_index}/{total} 个片段 MiniMax 状态: {status or '等待中'} (轮询 #{poll_attempt})",
                        min(70, base_progress + min(segment_span - 1, poll_attempt // 2)),
                    )

            _publish_sub(db, task_id, total, segment_index, f"正在等待 MiniMax 生成第 {segment_index}/{total} 个片段...", base_progress)
            video_service.poll_and_download(
                minimax_task_id, output_path, holder_id=holder_id, on_poll=on_poll,
            )

            _publish_sub(db, task_id, total, segment_index, f"正在提取第 {segment_index}/{total} 个片段末帧...", base_progress + 1)
            ffmpeg_service.extract_last_frame(output_path, last_frame_path)
            _mark_segment_ready(db, task_id, segment_index, output_path, last_frame_path)
            logger.info("Segment %d/%d done -> %s", segment_index, total, output_path)
            return

        except Exception as e:
            last_error = e
            logger.exception("Segment %d attempt %d failed: %s", segment_index, attempt, e)
            _mark_segment_failed(db, task_id, segment_index, str(e), attempt)

    raise RuntimeError(f"Segment {segment_index} failed after {max_retries} retries: {last_error}")


def _publish_sub(
    db: Session,
    task_id: str,
    total: int,
    segment_index: int,
    message: str,
    progress: int,
) -> None:
    publish_progress(
        task_id,
        TaskStatus.SEGMENT_GENERATING.value,
        "segment_video",
        progress,
        message,
        current_segment=segment_index,
        total_segments=total,
    )
    _update_task_message(db, task_id, progress, message)
