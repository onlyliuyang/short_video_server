# Short Video Generator

基于 MiniMax API 的 3 分钟短视频自动生成 Web 服务。

## 功能

- 用户输入视频创作方案（主题、风格、受众等）
- MiniMax LLM 生成完整脚本并拆分为 **30×6 秒** 分镜
- **首尾帧衔接**：上一片段末帧作为下一片段首帧
- MiniMax 视频 API 逐段生成（全局并发上限 3）
- MiniMax TTS 自动配音 + FFmpeg 合成字幕
- Redis + Celery 异步队列
- 前端 SSE 实时进度 + 预览播放与下载

## 技术栈

- **后端**: FastAPI + Celery + Redis + PostgreSQL
- **前端**: Next.js 15 + TypeScript + Tailwind CSS
- **媒体**: FFmpeg

## 快速开始

### 1. 环境准备

- Docker & Docker Compose
- Node.js 18+
- FFmpeg（本地开发 Worker 需要）

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env，填入 MINIMAX_API_KEY
```

### 3. 启动基础设施

```bash
docker compose up -d postgres redis
```

### 4. 启动后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 5. 启动 Celery Worker

**macOS 本地开发（必看）**：默认 `prefork` 池在 macOS + Python 3.13 上容易触发 `SIGSEGV`，请用 `solo` 池：

```bash
cd backend
source ../venv/bin/activate   # 或 source .venv/bin/activate

# 推荐：使用启动脚本
chmod +x ../scripts/worker.sh
../scripts/worker.sh

# 或手动启动
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
python -m celery -A app.workers.celery_app worker \
  --pool=solo \
  --loglevel=info \
  -Q celery,default,video_gen,media,tts
```

**Linux / Docker 生产环境**：

```bash
celery -A app.workers.celery_app worker --loglevel=info -Q celery,default,video_gen,media,tts --concurrency=4
```

### 6. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

### Docker 一键启动（API + Worker）

```bash
docker compose up -d
```

## API 端点

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/tasks` | 创建视频生成任务 |
| GET | `/api/v1/tasks/{id}` | 获取任务详情 |
| GET | `/api/v1/tasks/{id}/events` | SSE 实时进度 |
| POST | `/api/v1/tasks/{id}/retry` | 失败重试 |
| GET | `/api/v1/health` | 健康检查 |

## 配置项

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SEGMENT_COUNT` | 30 | 片段数量 |
| `SEGMENT_DURATION_SEC` | 6 | 每段时长（秒） |
| `VIDEO_CONCURRENCY` | 3 | MiniMax 视频 API 并发上限 |
| `VIDEO_RESOLUTION` | 1080P | 视频分辨率 |
| `STORAGE_PATH` | ./storage | 本地存储路径 |

## 项目结构

```
short_video_server/
├── backend/          # FastAPI + Celery
├── frontend/         # Next.js
├── storage/          # 本地视频文件
├── docker-compose.yml
└── .env.example
```

## 注意事项

- 完整生成 30 段视频耗时较长（取决于 MiniMax API 队列），请耐心等待
- 首尾帧衔接要求片段**串行生成**，单任务内无法并行
- 全局并发上限 3 指同时进行的 MiniMax 视频 API 调用数（跨任务共享）
- 生产环境请将 `STORAGE_PATH` 迁移至 OSS
# short_video_server
