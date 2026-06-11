from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.providers.base import TTSProviderCapabilities
from app.providers.constants import TTS_MINIMAX
from app.services.minimax_tts import MiniMaxTTSService


class MiniMaxTTSProvider:
    provider_id = TTS_MINIMAX

    def __init__(self) -> None:
        self._svc = MiniMaxTTSService()

    def capabilities(self) -> TTSProviderCapabilities:
        return TTSProviderCapabilities(
            provider_id=self.provider_id,
            display_name="MiniMax 配音",
            default_voice_id=settings.minimax_tts_voice_id,
            supports_timeline_mix=True,
        )

    def synthesize(self, text: str, output_path: Path, voice_id: str | None = None) -> None:
        self._svc.synthesize(text, output_path)


minimax_tts_provider = MiniMaxTTSProvider()
