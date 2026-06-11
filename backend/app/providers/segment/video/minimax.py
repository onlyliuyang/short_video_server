from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import settings
from app.providers.base import (
    CreateSegmentJobRequest,
    SegmentPromptContext,
    SegmentProviderCapabilities,
)
from app.providers.constants import GENERATION_MODE_VIDEO, VIDEO_MINIMAX_HAILUO
from app.providers.prompt_loader import render_segment_prompt
from app.services.minimax_video import video_service

logger = logging.getLogger(__name__)


class MiniMaxHailuoVideoProvider:
    provider_id = VIDEO_MINIMAX_HAILUO
    generation_mode = GENERATION_MODE_VIDEO

    def capabilities(self) -> SegmentProviderCapabilities:
        return SegmentProviderCapabilities(
            provider_id=self.provider_id,
            display_name="MiniMax 海螺",
            generation_mode="video",
            max_duration_sec=10,
            allowed_durations=[6, 10],
            supported_resolutions=[settings.video_resolution],
            supports_first_frame=True,
            supports_last_frame=True,
            default_concurrency=settings.video_concurrency,
            estimated_cost_hint="按量计费",
        )

    def build_prompt(self, ctx: SegmentPromptContext) -> str:
        scene = ctx.scene_prompt or ctx.visual_description or ""
        start_visual = ctx.seg_data.get("start_visual_description", "")
        continuity = start_visual or ctx.prev_end_visual
        motion = ctx.seg_data.get("motion_in_shot", "")
        return render_segment_prompt(
            self.provider_id,
            "video_prompt",
            setting_anchor=ctx.setting_anchor,
            setting_keywords=ctx.setting_keywords,
            user_prompt=ctx.user_prompt,
            scene=scene,
            shot_type=ctx.seg_data.get("shot_type", ""),
            segment_index=ctx.segment_index,
            start_visual=start_visual,
            prev_end_visual=ctx.prev_end_visual,
            continuity=continuity,
            motion=motion,
            camera_movement=ctx.camera_movement,
            global_style=ctx.global_style,
            end_visual=ctx.seg_data.get("end_visual_description", ""),
            transition=ctx.seg_data.get("transition_to_next", ""),
        ).strip()

    def create_job(self, req: CreateSegmentJobRequest) -> str:
        first_frame = req.first_frame_path if req.first_frame_path and req.first_frame_path.exists() else None
        if req.first_frame_path and not first_frame:
            logger.warning("[MiniMax Video] first_frame missing: %s", req.first_frame_path)
        last_frame = req.last_frame_path if req.last_frame_path and req.last_frame_path.exists() else None
        return video_service.create_video_task(
            prompt=req.prompt,
            duration=req.duration_sec,
            first_frame_path=first_frame,
            last_frame_path=last_frame,
            holder_id=req.holder_id,
        )

    def poll_and_download(
        self,
        job_id: str,
        output_path: Path,
        *,
        holder_id: str,
        on_poll=None,
    ) -> None:
        video_service.poll_and_download(job_id, output_path, holder_id=holder_id, on_poll=on_poll)


minimax_hailuo_provider = MiniMaxHailuoVideoProvider()
