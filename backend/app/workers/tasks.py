import logging
import traceback
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.core.sync_database import SyncSessionLocal
from app.models import FinalOutput, SegmentStatus, StoryboardSegment, TaskEvent, TaskStatus, VideoTask
from app.services.ffmpeg_service import ffmpeg_service
from app.services.llm_service import llm_service
from app.services.minimax_tts import tts_service
from app.services.storage_service import storage_service
from app.utils.logging_config import setup_logging
from app.utils.progress import acquire_task_lock, publish_progress, release_task_lock
from app.workers.celery_app import celery_app
from app.workers.tasks_segment import generate_single_segment

setup_logging()
logger = logging.getLogger(__name__)


def _update_task(db, task_id: uuid.UUID, **kwargs) -> None:
    db.query(VideoTask).filter(VideoTask.id == task_id).update(kwargs)
    db.commit()


def _log_event(db, task_id: uuid.UUID, stage: str, message: str, payload: dict | None = None) -> None:
    event = TaskEvent(task_id=task_id, stage=stage, message=message, payload=payload)
    db.add(event)
    db.commit()


def _first_pending_segment(db, task_id: uuid.UUID, total: int) -> int:
    rows = (
        db.query(StoryboardSegment.segment_index)
        .filter(
            StoryboardSegment.task_id == task_id,
            StoryboardSegment.status == SegmentStatus.VIDEO_READY.value,
        )
        .all()
    )
    ready = {row[0] for row in rows}
    for i in range(1, total + 1):
        if i not in ready:
            return i
    return total + 1


def _ensure_storyboard(db, task: VideoTask, script_data: dict) -> None:
    existing = db.query(StoryboardSegment).filter(StoryboardSegment.task_id == task.id).count()
    if existing == task.total_segments:
        return
    db.query(StoryboardSegment).filter(StoryboardSegment.task_id == task.id).delete()
    for seg in script_data["segments"]:
        db.add(StoryboardSegment(
            task_id=task.id,
            segment_index=seg["index"],
            scene_prompt=seg.get("scene_prompt", ""),
            narration_text=seg.get("narration", ""),
            subtitle_text=seg.get("subtitle", seg.get("narration", "")),
            visual_description=seg.get("visual_description", ""),
            camera_movement=seg.get("camera_movement", ""),
        ))
    db.commit()


def _truncate(text: str, max_len: int = 480) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _synthesize_timeline_voiceover(
    task_id: str,
    script_data: dict,
    segment_duration: int,
    total_segments: int,
    voice_path,
) -> None:
    """按分段时间轴生成分段 TTS 并混合，避免整段旁白过短导致成片被裁切。"""
    from pathlib import Path

    tts_dir = storage_service.task_dir(task_id) / "tts_parts"
    tts_dir.mkdir(parents=True, exist_ok=True)
    transition_sec = settings.segment_transition_sec
    tracks: list[tuple[Path, float]] = []

    for i, seg in enumerate(script_data["segments"]):
        part_path = tts_dir / f"seg_{i + 1}.mp3"
        narration = seg.get("narration", "").strip()
        if narration and (not part_path.exists() or part_path.stat().st_size == 0):
            tts_service.synthesize(narration, part_path)
        if part_path.exists() and part_path.stat().st_size > 0:
            start = ffmpeg_service.segment_start_sec(i, segment_duration, transition_sec)
            tracks.append((part_path, start))

    expected_dur = ffmpeg_service.expected_video_duration(
        total_segments, segment_duration, transition_sec,
    )
    if not tracks:
        logger.warning("No TTS tracks for task=%s, skip voiceover", task_id)
        return

    ffmpeg_service.mix_audio_timeline(tracks, voice_path, total_duration=expected_dur)
    logger.info(
        "Timeline voiceover done task=%s tracks=%d expected=%.2fs actual=%.2fs",
        task_id, len(tracks), expected_dur, ffmpeg_service.get_duration_sec(voice_path),
    )


def _compose_and_finish(
    db,
    tid: uuid.UUID,
    task_id: str,
    task: VideoTask,
    script_data: dict,
) -> None:
    voice_path = storage_service.voiceover_path(task_id)
    subtitle_path = storage_service.subtitle_path(task_id)
    concat_path = storage_service.task_dir(task_id) / "concat.mp4"
    final_path = storage_service.final_video_path(task_id)

    if not voice_path.exists():
        _update_task(
            db, tid,
            status=TaskStatus.VOICEOVER_GENERATING.value,
            progress=75,
            progress_message="正在生成配音",
        )
        publish_progress(task_id, TaskStatus.VOICEOVER_GENERATING.value, "voiceover", 75, "正在生成配音")
        _synthesize_timeline_voiceover(
            task_id, script_data, task.segment_duration_sec, task.total_segments, voice_path,
        )
    else:
        expected_voice = ffmpeg_service.expected_video_duration(
            task.total_segments, task.segment_duration_sec, settings.segment_transition_sec,
        )
        actual_voice = ffmpeg_service.get_duration_sec(voice_path)
        if actual_voice < expected_voice * 0.85:
            logger.warning(
                "Voiceover too short (%.2fs < expected %.2fs), regenerating timeline TTS",
                actual_voice, expected_voice,
            )
            _synthesize_timeline_voiceover(
                task_id, script_data, task.segment_duration_sec, task.total_segments, voice_path,
            )
        else:
            logger.info("Skip TTS, voiceover exists: %s (%.2fs)", voice_path, actual_voice)

    if not subtitle_path.exists():
        ffmpeg_service.generate_srt(
            script_data["segments"],
            task.segment_duration_sec,
            subtitle_path,
            transition_sec=settings.segment_transition_sec,
        )

    if not concat_path.exists():
        segment_paths = [
            storage_service.segment_video_path(task_id, i)
            for i in range(1, task.total_segments + 1)
        ]
        ffmpeg_service.concat_videos(
            segment_paths,
            concat_path,
            transition_sec=settings.segment_transition_sec,
            transition_type=settings.segment_transition_type,
        )
        seg_durations = [ffmpeg_service.get_duration_sec(p) for p in segment_paths]
        concat_dur = ffmpeg_service.get_duration_sec(concat_path)
        logger.info(
            "Concat done task=%s segment_durations=%s concat=%.2fs expected=%.2fs",
            task_id, [round(d, 2) for d in seg_durations], concat_dur,
            ffmpeg_service.expected_video_duration(
                task.total_segments, task.segment_duration_sec, settings.segment_transition_sec,
            ),
        )
    else:
        logger.info("Skip concat, file exists: %s", concat_path)

    _update_task(
        db, tid,
        status=TaskStatus.COMPOSING.value,
        progress=90,
        progress_message="正在合成视频",
    )
    publish_progress(task_id, TaskStatus.COMPOSING.value, "compose", 90, "正在合成视频")

    ffmpeg_service.merge_audio_video(concat_path, voice_path, final_path, subtitle_path)

    final_dur = ffmpeg_service.get_duration_sec(final_path)
    concat_dur = ffmpeg_service.get_duration_sec(concat_path)
    voice_dur = ffmpeg_service.get_duration_sec(voice_path)
    logger.info(
        "Final output task=%s video=%.2fs concat=%.2fs voice=%.2fs",
        task_id, final_dur, concat_dur, voice_dur,
    )

    duration_ms = ffmpeg_service.get_duration_ms(final_path)
    file_size = final_path.stat().st_size if final_path.exists() else None

    db.query(FinalOutput).filter(FinalOutput.task_id == tid).delete()
    db.add(FinalOutput(
        task_id=tid,
        video_path=storage_service.to_relative_path(final_path),
        audio_path=storage_service.to_relative_path(voice_path),
        subtitle_path=storage_service.to_relative_path(subtitle_path),
        duration_ms=duration_ms,
        file_size_bytes=file_size,
    ))

    _update_task(
        db, tid,
        status=TaskStatus.COMPLETED.value,
        progress=100,
        progress_message="已完成",
        completed_at=datetime.now(timezone.utc),
        error_message=None,
    )
    publish_progress(task_id, TaskStatus.COMPLETED.value, "completed", 100, "已完成")
    _log_event(db, tid, "completed", "视频生成完成")


@celery_app.task(bind=True, name="app.workers.tasks.run_pipeline")
def run_pipeline(self, task_id: str, resume: bool = False) -> None:
    if not acquire_task_lock(task_id):
        logger.warning("Pipeline already running for task %s, skip duplicate", task_id)
        return

    db = SyncSessionLocal()
    tid = uuid.UUID(task_id)
    task_progress = 0
    try:
        task = db.query(VideoTask).filter(VideoTask.id == tid).one()
        task_progress = task.progress

        can_resume = (
            resume
            and task.script_json
            and db.query(StoryboardSegment).filter(StoryboardSegment.task_id == tid).count() == task.total_segments
        )

        if can_resume:
            logger.info("Resuming pipeline task=%s from existing storyboard", task_id)
            script_data = task.script_json
            _update_task(
                db, tid,
                status=TaskStatus.SEGMENT_GENERATING.value,
                error_message=None,
                progress_message="正在恢复视频生成",
            )
            publish_progress(task_id, TaskStatus.SEGMENT_GENERATING.value, "segment_video", task.progress, "正在恢复视频生成")
        else:
            _update_task(
                db, tid,
                status=TaskStatus.SCRIPT_GENERATING.value,
                progress=5,
                progress_message="正在生成脚本",
                error_message=None,
            )
            publish_progress(task_id, TaskStatus.SCRIPT_GENERATING.value, "script", 5, "正在生成脚本")
            _log_event(db, tid, "script", "正在生成脚本")

            cfg = task.input_config
            script_data = llm_service.generate_script_and_storyboard(
                prompt=cfg.get("prompt", ""),
                theme=cfg.get("theme"),
                style=cfg.get("style"),
                audience=cfg.get("audience"),
                script_direction=cfg.get("script_direction"),
                segment_count=task.total_segments,
                segment_duration_sec=task.segment_duration_sec,
            )
            for seg in script_data.get("segments", []):
                logger.info(
                    "[Storyboard] seg=%s shot=%s camera=%s scene_prompt=%s",
                    seg.get("index"),
                    seg.get("shot_type", "-"),
                    seg.get("camera_movement", "-"),
                    seg.get("scene_prompt", ""),
                )

            _update_task(
                db, tid,
                status=TaskStatus.STORYBOARD_GENERATING.value,
                script_json=script_data,
                progress=10,
                progress_message="正在拆分分镜",
            )
            publish_progress(task_id, TaskStatus.STORYBOARD_GENERATING.value, "storyboard", 10, "正在拆分分镜")
            _ensure_storyboard(db, task, script_data)

        ffmpeg_service.ensure_available()

        start_segment = _first_pending_segment(db, tid, task.total_segments)
        if start_segment > task.total_segments:
            logger.info("All segments ready, continue to TTS/compose task=%s", task_id)
        else:
            _update_task(
                db, tid,
                status=TaskStatus.SEGMENT_GENERATING.value,
                progress_message=f"正在生成第 {start_segment} 个视频片段",
            )

        for i in range(start_segment, task.total_segments + 1):
            progress = 15 + int((i / task.total_segments) * 55)
            publish_progress(
                task_id,
                TaskStatus.SEGMENT_GENERATING.value,
                "segment_video",
                progress,
                f"正在生成第 {i}/{task.total_segments} 个视频片段",
                current_segment=i,
                total_segments=task.total_segments,
            )
            _update_task(db, tid, progress=progress, progress_message=f"正在生成第 {i}/{task.total_segments} 个视频片段")
            generate_single_segment(db, task_id, i)

        _compose_and_finish(db, tid, task_id, task, script_data)

    except Exception as e:
        db.rollback()
        tb = traceback.format_exc()
        logger.exception("Pipeline failed task=%s", task_id)
        row = db.query(VideoTask).filter(VideoTask.id == tid).first()
        progress = row.progress if row else task_progress
        err = _truncate(str(e))
        if row:
            _update_task(
                db, tid,
                status=TaskStatus.FAILED.value,
                error_message=err,
                progress_message=f"失败: {err}",
            )
            _log_event(db, tid, "failed", err, {"traceback": tb})
        publish_progress(task_id, TaskStatus.FAILED.value, "failed", progress, f"失败: {err}")
        raise
    finally:
        db.close()
        release_task_lock(task_id)


@celery_app.task(bind=True, name="app.workers.tasks.compose_only")
def compose_only(self, task_id: str) -> None:
    """仅重试合成阶段（片段与配音已就绪时使用）。"""
    if not acquire_task_lock(task_id):
        return
    db = SyncSessionLocal()
    tid = uuid.UUID(task_id)
    try:
        task = db.query(VideoTask).filter(VideoTask.id == tid).one()
        if not task.script_json:
            raise RuntimeError("缺少脚本数据，无法合成")
        _compose_and_finish(db, tid, task_id, task, task.script_json)
    except Exception as e:
        db.rollback()
        err = _truncate(str(e))
        row = db.query(VideoTask).filter(VideoTask.id == tid).first()
        if row:
            _update_task(db, tid, status=TaskStatus.FAILED.value, error_message=err, progress_message=f"失败: {err}")
        publish_progress(task_id, TaskStatus.FAILED.value, "failed", row.progress if row else 90, f"失败: {err}")
        raise
    finally:
        db.close()
        release_task_lock(task_id)


@celery_app.task(bind=True, name="app.workers.tasks.retry_pipeline")
def retry_pipeline(self, task_id: str) -> None:
    db = SyncSessionLocal()
    try:
        tid = uuid.UUID(task_id)
        task = db.query(VideoTask).filter(VideoTask.id == tid).one()
        _update_task(
            db, tid,
            status=TaskStatus.PENDING.value,
            progress_message="正在重试...",
            error_message=None,
        )
        publish_progress(task_id, TaskStatus.PENDING.value, "pending", task.progress, "正在重试...")
    finally:
        db.close()

    # 若片段与配音已完成，仅重跑合成
    voice_path = storage_service.voiceover_path(task_id)
    task = None
    start_seg = 1
    db = SyncSessionLocal()
    try:
        task = db.query(VideoTask).filter(VideoTask.id == uuid.UUID(task_id)).one()
        start_seg = _first_pending_segment(db, task.id, task.total_segments)
    finally:
        db.close()

    if task and start_seg > task.total_segments and voice_path.exists() and task.script_json:
        compose_only.delay(task_id)
    else:
        run_pipeline.delay(task_id, resume=True)
