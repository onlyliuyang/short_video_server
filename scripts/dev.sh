#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  echo "请先复制 .env.example 为 .env 并填入 MINIMAX_API_KEY"
  cp -n .env.example .env 2>/dev/null || true
  exit 1
fi

echo "启动 Postgres + Redis..."
docker compose up -d postgres redis

echo "等待数据库就绪..."
sleep 3

echo "启动 API (8000)..."
cd backend
if [ ! -d .venv ]; then
  python3 -m venv .venv 2>/dev/null || true
fi
source .venv/bin/activate 2>/dev/null || true
pip install -r requirements.txt -q 2>/dev/null || echo "提示: 本地 Python 版本较低时请使用 docker compose up"

uvicorn app.main:app --reload --host 0.0.0.0 --port 8080 &
API_PID=$!

echo "启动 Celery Worker..."
celery -A app.workers.celery_app worker --loglevel=info -Q default,video_gen,media,tts --concurrency=4 &
WORKER_PID=$!

cd "$ROOT/frontend"
echo "启动前端 (3000)..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "服务已启动:"
echo "  前端: http://localhost:3000"
echo "  API:  http://localhost:8080/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

trap "kill $API_PID $WORKER_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
