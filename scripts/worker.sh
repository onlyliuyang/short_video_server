#!/usr/bin/env bash
# macOS 本地开发 Worker 启动脚本（避免 prefork + fork 导致 SIGSEGV）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

if [ -f "$ROOT/venv/bin/activate" ]; then
  source "$ROOT/venv/bin/activate"
elif [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH}"

POOL="${CELERY_POOL:-solo}"
CONCURRENCY="${CELERY_CONCURRENCY:-1}"
QUEUES="${CELERY_QUEUES:-celery,default,video_gen,media,tts}"

echo "Starting Celery worker (pool=$POOL, concurrency=$CONCURRENCY)..."

exec python -m celery -A app.workers.celery_app worker \
  --loglevel=info \
  --pool="$POOL" \
  --concurrency="$CONCURRENCY" \
  -Q "$QUEUES"
