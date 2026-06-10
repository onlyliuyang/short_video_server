from fastapi import APIRouter

from app.core.config import settings
from app.schemas.config import VideoConfigResponse

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/video", response_model=VideoConfigResponse)
async def get_video_config():
    return VideoConfigResponse(
        segment_count=settings.segment_count,
        segment_duration_sec=settings.segment_duration_sec,
        total_duration_sec=settings.effective_total_duration_sec,
        segment_transition_sec=settings.segment_transition_sec,
        video_resolution=settings.video_resolution,
        video_concurrency=settings.video_concurrency,
    )
