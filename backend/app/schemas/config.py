from pydantic import BaseModel


class VideoConfigResponse(BaseModel):
    segment_count: int
    segment_duration_sec: int
    total_duration_sec: int
    segment_transition_sec: float
    video_resolution: str
    video_concurrency: int
