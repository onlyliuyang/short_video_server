from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimaxi.com"
    minimax_llm_model: str = "MiniMax-M2.5"
    minimax_video_model: str = "MiniMax-Hailuo-2.3"
    minimax_tts_model: str = "speech-02-hd"
    minimax_tts_voice_id: str = "Chinese (Mandarin)_Reliable_Executive"

    database_url: str = "postgresql+asyncpg://shortvideo:shortvideo@localhost:5432/shortvideo"
    database_url_sync: str = "postgresql+psycopg://shortvideo:shortvideo@localhost:5432/shortvideo"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    storage_path: str = "./storage"
    storage_public_url: str = "http://localhost:8080/media"

    segment_count: int = 30
    segment_duration_sec: int = 6
    segment_transition_sec: float = 0.4
    segment_transition_type: str = "fade"
    video_resolution: str = "1080P"
    video_concurrency: int = 3
    minimax_prompt_optimizer: bool = False

    # image | video — image=文生图+FFmpeg，video=海螺视频（付费开启）
    generation_mode: str = "image"
    minimax_image_model: str = "image-01"
    image_aspect_ratio: str = "16:9"
    image_concurrency: int = 5

    # Multi-provider defaults
    default_llm_provider: str = "minimax_llm"
    default_tts_provider: str = "minimax_tts"
    default_generation_mode: str = "image"
    enabled_llm_providers: str = "minimax_llm"
    enabled_tts_providers: str = "minimax_tts"
    enabled_image_providers: str = "minimax_image"
    enabled_video_providers: str = "minimax_hailuo"
    prompt_hot_reload: bool = False
    prompt_dir: str = ""

    @property
    def is_image_mode(self) -> bool:
        return self.generation_mode.strip().lower() != "video"

    @property
    def effective_total_duration_sec(self) -> int:
        """成片时长（含段间转场重叠）。"""
        n = self.segment_count
        d = self.segment_duration_sec
        t = self.segment_transition_sec
        if n <= 0:
            return 0
        if n == 1 or t <= 0:
            return n * d
        return int(n * d - (n - 1) * t)

    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
