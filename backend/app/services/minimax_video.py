import base64
import copy
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from app.core.config import settings
from app.utils.progress import video_limiter

logger = logging.getLogger(__name__)


def _safe_json(data: Any, max_len: int = 2000) -> str:
    text = json.dumps(data, ensure_ascii=False, default=str)
    if len(text) > max_len:
        return text[:max_len] + "...(truncated)"
    return text


def _payload_for_log(payload: dict) -> dict:
    logged = copy.deepcopy(payload)
    for key in ("first_frame_image", "last_frame_image"):
        if key in logged and logged[key]:
            val = str(logged[key])
            logged[key] = f"<base64 {len(val)} chars>" if len(val) > 80 else val
    return logged


class MiniMaxVideoService:
    POLL_INTERVAL = 5
    MAX_POLL_ATTEMPTS = 360  # ~30 min

    def __init__(self) -> None:
        self.base_url = settings.minimax_base_url.rstrip("/")
        self._auth_headers = {
            "Authorization": f"Bearer {settings.minimax_api_key}",
            "Content-Type": "application/json",
        }

    def _frame_to_data_url(self, frame_path: Path) -> str:
        data = frame_path.read_bytes()
        b64 = base64.b64encode(data).decode("utf-8")
        logger.info("Encode frame %s (%d bytes) -> base64", frame_path, len(data))
        return f"data:image/jpeg;base64,{b64}"

    def create_video_task(
        self,
        prompt: str,
        duration: int = 6,
        first_frame_path: Path | None = None,
        last_frame_path: Path | None = None,
        holder_id: str = "default",
    ) -> str:
        logger.info(
            "[MiniMax Video] create task holder=%s model=%s duration=%ds resolution=%s",
            holder_id, settings.minimax_video_model, duration, settings.video_resolution,
        )
        logger.info("[MiniMax Video] prompt: %s", prompt[:500] + ("..." if len(prompt) > 500 else ""))

        if not video_limiter.acquire(holder_id):
            raise TimeoutError("Timed out waiting for video generation slot (max concurrent=%s)" % settings.video_concurrency)

        try:
            payload: dict = {
                "model": settings.minimax_video_model,
                "prompt": prompt,
                "duration": duration,
                "resolution": settings.video_resolution,
                "prompt_optimizer": settings.minimax_prompt_optimizer,
            }

            if first_frame_path and first_frame_path.exists():
                payload["first_frame_image"] = self._frame_to_data_url(first_frame_path)
                logger.info("[MiniMax Video] using first_frame: %s", first_frame_path)
            elif first_frame_path:
                logger.warning("[MiniMax Video] first_frame missing: %s", first_frame_path)

            if last_frame_path and last_frame_path.exists():
                payload["last_frame_image"] = self._frame_to_data_url(last_frame_path)
                logger.info("[MiniMax Video] using last_frame: %s", last_frame_path)

            url = f"{self.base_url}/v1/video_generation"
            logger.info("[MiniMax Video] POST %s payload=%s", url, _safe_json(_payload_for_log(payload)))

            with httpx.Client(timeout=60) as client:
                resp = client.post(url, headers=self._auth_headers, json=payload)
                logger.info("[MiniMax Video] create HTTP %s body=%s", resp.status_code, resp.text[:2000])
                resp.raise_for_status()
                data = resp.json()
                base_resp = data.get("base_resp", {})
                if base_resp.get("status_code", 0) != 0:
                    raise RuntimeError(f"MiniMax video API error: {base_resp}")
                task_id = data.get("task_id") or data.get("taskId")
                if not task_id:
                    raise RuntimeError(f"MiniMax create response missing task_id: {_safe_json(data)}")
                logger.info("[MiniMax Video] created task_id=%s", task_id)
                return task_id
        except Exception:
            video_limiter.release(holder_id)
            logger.exception("[MiniMax Video] create failed holder=%s", holder_id)
            raise

    def poll_and_download(
        self,
        minimax_task_id: str,
        output_path: Path,
        holder_id: str = "default",
        on_poll: Callable[[int, str, dict], None] | None = None,
    ) -> None:
        try:
            logger.info("[MiniMax Video] polling task_id=%s holder=%s", minimax_task_id, holder_id)
            file_id = self._poll_until_success(minimax_task_id, on_poll=on_poll)
            logger.info("[MiniMax Video] task success file_id=%s", file_id)
            download_url = self._get_download_url(file_id)
            logger.info("[MiniMax Video] download_url=%s", download_url[:200])
            self._download_file(download_url, output_path)
            logger.info("[MiniMax Video] saved %s (%d bytes)", output_path, output_path.stat().st_size)
        finally:
            video_limiter.release(holder_id)

    def _poll_until_success(self, task_id: str, on_poll: Callable[[int, str, dict], None] | None = None) -> str:
        url = f"{self.base_url}/v1/query/video_generation"
        with httpx.Client(timeout=30) as client:
            for attempt in range(1, self.MAX_POLL_ATTEMPTS + 1):
                resp = client.get(url, headers=self._auth_headers, params={"task_id": task_id})
                raw = resp.text
                logger.info(
                    "[MiniMax Video] poll #%d task_id=%s HTTP %s body=%s",
                    attempt, task_id, resp.status_code, raw[:2000],
                )
                resp.raise_for_status()
                data = resp.json()
                base_resp = data.get("base_resp", {})
                if base_resp.get("status_code", 0) != 0:
                    raise RuntimeError(f"MiniMax query error: {base_resp}")

                status = data.get("status", "")
                if on_poll:
                    on_poll(attempt, status, data)

                if status == "Success":
                    file_id = data.get("file_id")
                    if not file_id:
                        raise RuntimeError(f"Video succeeded but no file_id: {_safe_json(data)}")
                    return file_id
                if status == "Fail":
                    raise RuntimeError(f"Video generation failed: {_safe_json(data)}")

                if attempt % 6 == 0:
                    logger.info(
                        "[MiniMax Video] still waiting task_id=%s status=%s attempt=%d/%d",
                        task_id, status, attempt, self.MAX_POLL_ATTEMPTS,
                    )
                time.sleep(self.POLL_INTERVAL)

        raise TimeoutError(f"Video task {task_id} timed out after {self.MAX_POLL_ATTEMPTS * self.POLL_INTERVAL}s")

    def _get_download_url(self, file_id: str) -> str:
        url = f"{self.base_url}/v1/files/retrieve"
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=self._auth_headers, params={"file_id": file_id})
            logger.info("[MiniMax Video] retrieve file_id=%s HTTP %s body=%s", file_id, resp.status_code, resp.text[:2000])
            resp.raise_for_status()
            data = resp.json()
            base_resp = data.get("base_resp", {})
            if base_resp.get("status_code", 0) != 0:
                raise RuntimeError(f"MiniMax file retrieve error: {base_resp}")

            file_info = data.get("file", {})
            download_url = file_info.get("download_url") or file_info.get("backup_download_url")
            if not download_url:
                raise RuntimeError(f"No download URL for file_id {file_id}: {_safe_json(data)}")
            return download_url

    def _download_file(self, url: str, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=300, follow_redirects=True) as client:
            with client.stream("GET", url) as resp:
                logger.info("[MiniMax Video] download HTTP %s", resp.status_code)
                resp.raise_for_status()
                total = 0
                with open(output_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        total += len(chunk)
                logger.info("[MiniMax Video] downloaded %d bytes -> %s", total, output_path)


video_service = MiniMaxVideoService()
