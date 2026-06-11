export interface VideoConfig {
  segment_count: number;
  segment_duration_sec: number;
  total_duration_sec: number;
  segment_transition_sec?: number;
  generation_mode: string;
  video_resolution: string;
  video_concurrency: number;
  image_aspect_ratio?: string;
}

export interface ProviderCapabilities {
  max_duration_sec: number;
  allowed_durations?: number[];
  supported_resolutions?: string[];
  supported_aspect_ratios?: string[];
  supports_first_frame?: boolean;
  supports_last_frame?: boolean;
  hard_cut_between_segments?: boolean;
  default_concurrency?: number;
  estimated_cost_hint?: string | null;
}

export interface ProviderOption {
  id: string;
  label: string;
  enabled: boolean;
  disabled_reason?: string | null;
  capabilities?: ProviderCapabilities;
}

export interface ProvidersConfig {
  defaults: {
    generation_mode: string;
    llm_provider: string;
    tts_provider: string;
    segment_provider: string;
  };
  generation_modes: { id: string; label: string; description: string }[];
  llm_providers: ProviderOption[];
  tts_providers: ProviderOption[];
  segment_providers: Record<string, ProviderOption[]>;
}

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export interface TaskSegment {
  id: string;
  segment_index: number;
  status: string;
  narration_text?: string;
  subtitle_text?: string;
  visual_description?: string;
  camera_movement?: string;
  video_url?: string;
  image_url?: string;
  error_message?: string;
}

export interface TaskOutput {
  video_url: string;
  duration_ms?: number;
  file_size_bytes?: number;
}

export interface Task {
  id: string;
  status: string;
  progress: number;
  progress_message?: string;
  input_config: Record<string, unknown>;
  total_segments: number;
  segment_duration_sec: number;
  error_message?: string;
  created_at: string;
  completed_at?: string;
  segments: TaskSegment[];
  output?: TaskOutput;
}

export interface ProgressEvent {
  task_id: string;
  status: string;
  stage: string;
  progress: number;
  message: string;
  current_segment?: number;
  total_segments?: number;
  timestamp: string;
}

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let id = localStorage.getItem("session_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("session_id", id);
  }
  return id;
}

export async function getVideoConfig(): Promise<VideoConfig> {
  const res = await fetch(`${API_BASE}/api/v1/config/video`, { cache: "no-store" });
  if (!res.ok) throw new Error("获取视频配置失败");
  return res.json();
}

export async function getProvidersConfig(): Promise<ProvidersConfig> {
  const res = await fetch(`${API_BASE}/api/v1/config/providers`, { cache: "no-store" });
  if (!res.ok) throw new Error("获取 Provider 配置失败");
  return res.json();
}

export function resolveMediaUrl(url: string | undefined): string {
  if (!url) return "";
  const idx = url.indexOf("/media/");
  if (idx >= 0) return url.slice(idx);
  if (url.startsWith("/media/")) return url;
  return url;
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds} 秒`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s > 0 ? `${m} 分 ${s} 秒` : `${m} 分钟`;
}

export async function createTask(data: {
  prompt: string;
  theme?: string;
  style?: string;
  audience?: string;
  script_direction?: string;
  generation_mode?: "image" | "video";
  llm_provider?: string;
  tts_provider?: string;
  segment_provider?: string;
}): Promise<Task> {
  const res = await fetch(`${API_BASE}/api/v1/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...data, session_id: getSessionId() }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.message || "创建任务失败");
  }
  return res.json();
}

export async function getTask(taskId: string): Promise<Task> {
  const res = await fetch(`${API_BASE}/api/v1/tasks/${taskId}`);
  if (!res.ok) throw new Error("获取任务失败");
  return res.json();
}

export async function listTasks(): Promise<{ items: Task[]; total: number }> {
  const sessionId = getSessionId();
  const res = await fetch(`${API_BASE}/api/v1/tasks?session_id=${sessionId}`);
  if (!res.ok) throw new Error("获取任务列表失败");
  return res.json();
}

export async function retryTask(taskId: string): Promise<Task> {
  const res = await fetch(`${API_BASE}/api/v1/tasks/${taskId}/retry`, { method: "POST" });
  if (!res.ok) throw new Error("重试失败");
  return res.json();
}

export function subscribeTaskProgress(
  taskId: string,
  onEvent: (event: ProgressEvent) => void,
): () => void {
  const source = new EventSource(`${API_BASE}/api/v1/tasks/${taskId}/events`);
  let closed = false;

  const close = () => {
    if (closed) return;
    closed = true;
    source.close();
  };

  source.addEventListener("progress", (e) => {
    try {
      const event: ProgressEvent = JSON.parse(e.data);
      onEvent(event);
      if (["completed", "failed", "cancelled"].includes(event.status)) {
        close();
      }
    } catch {
      /* ignore malformed event */
    }
  });

  // SSE 正常结束或网络断开都会触发 onerror，不应在此启动轮询
  source.onerror = () => {
    close();
  };

  return close;
}

export const STATUS_LABELS: Record<string, string> = {
  pending: "已提交任务",
  script_generating: "正在生成脚本",
  storyboard_generating: "正在拆分分镜",
  segment_generating: "正在生成视频片段",
  voiceover_generating: "正在生成配音",
  composing: "正在合成视频",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

export const STAGE_ORDER = [
  "pending",
  "script_generating",
  "storyboard_generating",
  "segment_generating",
  "voiceover_generating",
  "composing",
  "completed",
];
