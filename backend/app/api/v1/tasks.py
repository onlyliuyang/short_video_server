import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db
from app.schemas.task import CreateTaskRequest, TaskListResponse, TaskResponse
from app.services.task_service import build_task_response, create_task, get_task, list_tasks
from app.utils.progress import get_redis, progress_channel, progress_key
from app.workers.tasks import compose_only, retry_pipeline, run_pipeline

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
async def create_video_task(req: CreateTaskRequest, db: AsyncSession = Depends(get_db)):
    task = await create_task(db, req)
    task = await get_task(db, task.id)
    return build_task_response(task)


@router.get("", response_model=TaskListResponse)
async def get_tasks(
    session_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    tasks, total = await list_tasks(db, session_id=session_id, limit=limit)
    return TaskListResponse(
        items=[build_task_response(t) for t in tasks],
        total=total,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_video_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    task = await get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return build_task_response(task)


@router.get("/{task_id}/events")
async def task_events(task_id: UUID, db: AsyncSession = Depends(get_db)):
    task = await get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        r = get_redis()
        cached = r.get(progress_key(str(task_id)))
        if cached:
            yield {"event": "progress", "data": cached}

        if task.status in ("completed", "failed", "cancelled"):
            return

        pubsub = r.pubsub()
        pubsub.subscribe(progress_channel(str(task_id)))
        try:
            while True:
                message = await asyncio.to_thread(pubsub.get_message, timeout=1.0)
                if message and message["type"] == "message":
                    data = message["data"]
                    yield {"event": "progress", "data": data}
                    try:
                        parsed = json.loads(data)
                        if parsed.get("status") in ("completed", "failed", "cancelled"):
                            break
                    except json.JSONDecodeError:
                        pass
                await asyncio.sleep(0.1)
        finally:
            pubsub.unsubscribe(progress_channel(str(task_id)))
            pubsub.close()

    return EventSourceResponse(event_generator())


@router.post("/{task_id}/compose", response_model=TaskResponse)
async def compose_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    """仅重试视频合成（片段与配音已就绪时）。"""
    task = await get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.script_json:
        raise HTTPException(status_code=400, detail="缺少脚本，无法合成")

    compose_only.delay(str(task_id))
    return build_task_response(task)


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    task = await get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in ("failed", "cancelled"):
        raise HTTPException(status_code=400, detail="Only failed or cancelled tasks can be retried")

    retry_pipeline.delay(str(task_id))
    return build_task_response(task)
