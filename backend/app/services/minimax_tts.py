import base64
from pathlib import Path

import httpx

from app.core.config import settings


class MiniMaxTTSService:
    def __init__(self) -> None:
        self.base_url = settings.minimax_base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {settings.minimax_api_key}",
            "Content-Type": "application/json",
        }

    def synthesize(self, text: str, output_path: Path) -> None:
        payload = {
            "model": settings.minimax_tts_model,
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": settings.minimax_tts_voice_id,
                "speed": 1.0,
                "vol": 1.0,
                "pitch": 0,
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1,
            },
        }

        with httpx.Client(timeout=120) as client:
            resp = client.post(
                f"{self.base_url}/v1/t2a_v2",
                headers=self.headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

            base_resp = data.get("base_resp", {})
            if base_resp.get("status_code", 0) != 0:
                raise RuntimeError(f"MiniMax TTS error: {base_resp}")

            audio_hex = data.get("data", {}).get("audio")
            if not audio_hex:
                raise RuntimeError("No audio data in TTS response")

            audio_bytes = bytes.fromhex(audio_hex)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(audio_bytes)


tts_service = MiniMaxTTSService()
