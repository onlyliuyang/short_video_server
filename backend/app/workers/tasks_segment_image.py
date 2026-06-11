"""Backward-compatible re-export."""

from app.workers.tasks_segment import generate_single_segment as generate_single_segment_image

__all__ = ["generate_single_segment_image"]
