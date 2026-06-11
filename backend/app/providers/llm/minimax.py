from __future__ import annotations

import logging

from openai import OpenAI

from app.core.config import settings
from app.providers.base import LLMProviderCapabilities, StoryboardRequest
from app.providers.constants import LLM_MINIMAX
from app.providers.llm.storyboard_utils import enforce_setting_anchor, extract_json
from app.providers.prompt_loader import load_retry_suffix, load_system_prompt, render_user_prompt

logger = logging.getLogger(__name__)


class MiniMaxLLMProvider:
    provider_id = LLM_MINIMAX

    def __init__(self) -> None:
        self._client: OpenAI | None = None
        self.model = settings.minimax_llm_model

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=settings.minimax_api_key,
                base_url=f"{settings.minimax_base_url.rstrip('/')}/v1",
            )
        return self._client

    def capabilities(self) -> LLMProviderCapabilities:
        return LLMProviderCapabilities(
            provider_id=self.provider_id,
            display_name="MiniMax M2.5",
            max_output_tokens=16384,
        )

    def _chat(self, system: str, user: str, max_tokens: int = 8192, temperature: float = 0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_completion_tokens=max_tokens,
            temperature=temperature,
        )
        return (response.choices[0].message.content or "").strip()

    def generate_storyboard(self, req: StoryboardRequest) -> dict:
        mode = "video" if req.generation_mode.strip().lower() == "video" else "image"
        profile = req.prompt_profile

        system = load_system_prompt(profile, mode)
        user_msg = render_user_prompt(
            profile,
            mode,
            prompt=req.prompt,
            segment_count=req.segment_count,
            segment_duration_sec=req.segment_duration_sec,
            theme=req.theme,
            style=req.style,
            audience=req.audience,
            script_direction=req.script_direction,
        )

        logger.info("[LLM] provider=%s profile=%s mode=%s system_len=%d", self.provider_id, profile, mode, len(system))
        raw = self._chat(system, user_msg, max_tokens=16384, temperature=0.5)
        logger.info("[LLM] response length=%d preview=%s", len(raw), raw[:300])

        try:
            data = extract_json(raw)
        except ValueError:
            logger.warning("[LLM] JSON parse failed, retrying with strict prompt")
            suffix = load_retry_suffix(profile, mode)
            raw = self._chat(system + "\n" + suffix, user_msg, max_tokens=16384)
            logger.info("[LLM] retry response length=%d preview=%s", len(raw), raw[:300])
            data = extract_json(raw)

        segments = data.get("segments", [])
        if len(segments) != req.segment_count:
            raise ValueError(f"Expected {req.segment_count} segments, got {len(segments)}")

        for seg in segments:
            logger.info(
                "[LLM] storyboard seg=%s | shot=%s | scene_prompt=%s",
                seg.get("index"),
                seg.get("shot_type", "-"),
                seg.get("scene_prompt", ""),
            )

        return enforce_setting_anchor(data, req.prompt)


minimax_llm_provider = MiniMaxLLMProvider()
