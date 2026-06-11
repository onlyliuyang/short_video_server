"""Backward-compatible LLM service facade."""

from app.providers.base import StoryboardRequest
from app.providers.llm.minimax import minimax_llm_provider
from app.providers.llm.storyboard_utils import enforce_setting_anchor
from app.providers.registry import default_segment_provider


class MiniMaxLLMService:
    """Delegates to MiniMaxLLMProvider; kept for backward compatibility."""

    def generate_script_and_storyboard(
        self,
        prompt: str,
        theme: str | None,
        style: str | None,
        audience: str | None,
        script_direction: str | None,
        segment_count: int,
        segment_duration_sec: int,
        generation_mode: str = "image",
        prompt_profile: str | None = None,
    ) -> dict:
        profile = prompt_profile or default_segment_provider(
            "video" if generation_mode.strip().lower() == "video" else "image"
        )
        req = StoryboardRequest(
            prompt=prompt,
            theme=theme,
            style=style,
            audience=audience,
            script_direction=script_direction,
            segment_count=segment_count,
            segment_duration_sec=segment_duration_sec,
            generation_mode=generation_mode,
            prompt_profile=profile,
        )
        return minimax_llm_provider.generate_storyboard(req)

    @staticmethod
    def enforce_setting_anchor(script_data: dict, user_prompt: str) -> dict:
        return enforce_setting_anchor(script_data, user_prompt)


llm_service = MiniMaxLLMService()
