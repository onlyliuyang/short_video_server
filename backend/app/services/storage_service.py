import json
import os
import uuid
from pathlib import Path

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        self.base_path = Path(settings.storage_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def task_dir(self, task_id: str | uuid.UUID) -> Path:
        path = self.base_path / "tasks" / str(task_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def segment_video_path(self, task_id: str | uuid.UUID, index: int) -> Path:
        path = self.task_dir(task_id) / "segments" / f"seg_{index:02d}.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def segment_frame_path(self, task_id: str | uuid.UUID, index: int, frame: str = "last") -> Path:
        frames_dir = self.task_dir(task_id) / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        return frames_dir / f"seg_{index:02d}_{frame}.jpg"

    def voiceover_path(self, task_id: str | uuid.UUID) -> Path:
        return self.task_dir(task_id) / "voiceover.mp3"

    def subtitle_path(self, task_id: str | uuid.UUID) -> Path:
        return self.task_dir(task_id) / "subtitle.srt"

    def final_video_path(self, task_id: str | uuid.UUID) -> Path:
        return self.task_dir(task_id) / "final.mp4"

    def ensure_parent(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def to_public_url(self, path: str | Path) -> str:
        path = Path(path).resolve()
        rel = path.relative_to(self.base_path)
        return f"{settings.storage_public_url.rstrip('/')}/{rel.as_posix()}"

    def to_relative_path(self, path: str | Path) -> str:
        path = Path(path).resolve()
        return path.relative_to(self.base_path).as_posix()


storage_service = StorageService()
