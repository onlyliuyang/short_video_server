import logging
from pathlib import Path

import httpx

from app.core.config import settings
from app.services.minimax_errors import raise_for_base_resp
from app.utils.progress import image_limiter

logger = logging.getLogger(__name__)


class MiniMaxImageService:
    def __init__(self) -> None:
        self.base_url = settings.minimax_base_url.rstrip("/")
        self._auth_headers = {
            "Authorization": f"Bearer {settings.minimax_api_key}",
            "Content-Type": "application/json",
        }

    def generate_and_download(
        self,
        prompt: str,
        output_path: Path,
        holder_id: str = "default",
    ) -> None:
        logger.info(
            "[MiniMax Image] generate holder=%s model=%s ratio=%s prompt_len=%d",
            holder_id, settings.minimax_image_model, settings.image_aspect_ratio, len(prompt),
        )
        logger.info("[MiniMax Image] prompt: %s", prompt[:500] + ("..." if len(prompt) > 500 else ""))

        if not image_limiter.acquire(holder_id):
            raise TimeoutError(
                f"Timed out waiting for image generation slot (max concurrent={settings.image_concurrency})"
            )

        try:
            payload = {
                "model": settings.minimax_image_model,
                "prompt": prompt[:1500],
                "aspect_ratio": settings.image_aspect_ratio,
                "response_format": "url",
                "n": 1,
                "prompt_optimizer": False,
            }
            url = f"{self.base_url}/v1/image_generation"
            with httpx.Client(timeout=120) as client:
                resp = client.post(url, headers=self._auth_headers, json=payload)
                logger.info("[MiniMax Image] HTTP %s body=%s", resp.status_code, resp.text[:2000])
                resp.raise_for_status()
                data = resp.json()
                raise_for_base_resp(data.get("base_resp", {}))

                image_urls = (data.get("data") or {}).get("image_urls") or []
                if not image_urls:
                    raise RuntimeError(f"MiniMax image response missing image_urls: {data}")

                download_url = image_urls[0]
                self._download_file(download_url, output_path)
                logger.info("[MiniMax Image] saved %s (%d bytes)", output_path, output_path.stat().st_size)
        finally:
            image_limiter.release(holder_id)

    def _download_file(self, url: str, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        f.write(chunk)


image_service = MiniMaxImageService()
