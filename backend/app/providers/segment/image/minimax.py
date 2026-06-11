from __future__ import annotations

import logging
from pathlib import Path

import httpx

from app.core.config import settings
from app.providers.base import (
    CreateSegmentJobRequest,
    SegmentPromptContext,
    SegmentProviderCapabilities,
)
from app.providers.constants import GENERATION_MODE_IMAGE, IMAGE_MINIMAX
from app.providers.limiter import ProviderConcurrencyLimiter
from app.providers.prompt_loader import render_segment_prompt
from app.services.minimax_errors import raise_for_base_resp

logger = logging.getLogger(__name__)

_limiter = ProviderConcurrencyLimiter(IMAGE_MINIMAX, settings.image_concurrency)


class MiniMaxImageProvider:
    provider_id = IMAGE_MINIMAX
    generation_mode = GENERATION_MODE_IMAGE

    def capabilities(self) -> SegmentProviderCapabilities:
        return SegmentProviderCapabilities(
            provider_id=self.provider_id,
            display_name="MiniMax 文生图",
            generation_mode="image",
            max_duration_sec=60,
            supported_aspect_ratios=[settings.image_aspect_ratio],
            supports_first_frame=False,
            supports_last_frame=False,
            default_concurrency=settings.image_concurrency,
            estimated_cost_hint="按量计费",
        )

    def build_prompt(self, ctx: SegmentPromptContext) -> str:
        image_prompt = (
            ctx.seg_data.get("image_prompt")
            or ctx.scene_prompt
            or ctx.visual_description
            or ""
        ).strip()
        return render_segment_prompt(
            self.provider_id,
            "image_prompt",
            setting_anchor=ctx.setting_anchor,
            setting_keywords=ctx.setting_keywords,
            user_prompt=ctx.user_prompt,
            image_prompt=image_prompt,
            shot_type=ctx.seg_data.get("shot_type", ""),
            global_style=ctx.global_style,
        ).strip()

    def create_job(self, req: CreateSegmentJobRequest) -> str:
        if req.first_frame_path and req.first_frame_path.exists():
            logger.debug(
                "[MiniMax Image] first_frame provided but not supported, ignored: %s",
                req.first_frame_path,
            )
        if not _limiter.acquire(req.holder_id):
            raise TimeoutError(
                f"Timed out waiting for image generation slot (max concurrent={settings.image_concurrency})"
            )
        try:
            payload = {
                "model": settings.minimax_image_model,
                "prompt": req.prompt[:1500],
                "aspect_ratio": settings.image_aspect_ratio,
                "response_format": "url",
                "n": 1,
                "prompt_optimizer": False,
            }
            url = f"{settings.minimax_base_url.rstrip('/')}/v1/image_generation"
            headers = {
                "Authorization": f"Bearer {settings.minimax_api_key}",
                "Content-Type": "application/json",
            }
            logger.info("[MiniMax Image] prompt: %s", req.prompt[:500])
            with httpx.Client(timeout=120) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                raise_for_base_resp(data.get("base_resp", {}))
                image_urls = (data.get("data") or {}).get("image_urls") or []
                if not image_urls:
                    raise RuntimeError(f"MiniMax image response missing image_urls: {data}")
                return image_urls[0]
        except Exception:
            _limiter.release(req.holder_id)
            raise

    def poll_and_download(
        self,
        job_id: str,
        output_path: Path,
        *,
        holder_id: str,
        on_poll=None,
    ) -> None:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with httpx.Client(timeout=120, follow_redirects=True) as client:
                with client.stream("GET", job_id) as resp:
                    resp.raise_for_status()
                    with open(output_path, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=8192):
                            f.write(chunk)
            logger.info("[MiniMax Image] saved %s (%d bytes)", output_path, output_path.stat().st_size)
        finally:
            _limiter.release(holder_id)


minimax_image_provider = MiniMaxImageProvider()
