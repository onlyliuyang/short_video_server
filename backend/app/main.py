import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import config, health, tasks
from app.core.config import settings
from app.core.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Short Video Generator",
    description="MiniMax 3分钟短视频生成服务",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage_path = Path(settings.storage_path).resolve()
storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(storage_path)), name="media")

app.include_router(health.router, prefix="/api/v1")
app.include_router(config.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
