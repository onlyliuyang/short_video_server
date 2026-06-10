"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { ProgressTimeline } from "@/components/ProgressTimeline";
import { SegmentGrid } from "@/components/SegmentGrid";
import { VideoPlayer } from "@/components/VideoPlayer";
import {
  getTask,
  retryTask,
  subscribeTaskProgress,
  type ProgressEvent,
  type Task,
} from "@/lib/api";

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

export default function TaskDetailPage() {
  const params = useParams();
  const taskId = params.id as string;

  const [task, setTask] = useState<Task | null>(null);
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const taskRef = useRef<Task | null>(null);

  const refreshTask = useCallback(async () => {
    try {
      const data = await getTask(taskId);
      taskRef.current = data;
      setTask(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    }
  }, [taskId]);

  useEffect(() => {
    refreshTask();
  }, [refreshTask]);

  useEffect(() => {
    if (!taskId) return;
    return subscribeTaskProgress(taskId, (event) => {
      setProgress(event);
      if (TERMINAL_STATUSES.has(event.status)) {
        refreshTask();
        return;
      }
      setTask((prev) =>
        prev
          ? { ...prev, status: event.status, progress: event.progress, progress_message: event.message }
          : prev
      );
    });
  }, [taskId, refreshTask]);

  useEffect(() => {
    if (!taskId || !task || TERMINAL_STATUSES.has(task.status)) return;
    const interval = setInterval(() => {
      if (taskRef.current && TERMINAL_STATUSES.has(taskRef.current.status)) return;
      refreshTask();
    }, 15000);
    return () => clearInterval(interval);
  }, [taskId, task?.status, refreshTask]);

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await retryTask(taskId);
      await refreshTask();
    } catch (e) {
      setError(e instanceof Error ? e.message : "重试失败");
    } finally {
      setRetrying(false);
    }
  };

  if (error && !task) {
    return (
      <AppShell backHref="/" backLabel="← 返回创作">
        <div className="flex items-center justify-center flex-1">
          <p className="text-red-500">{error}</p>
        </div>
      </AppShell>
    );
  }

  if (!task) {
    return (
      <AppShell backHref="/" backLabel="← 返回创作">
        <div className="flex items-center justify-center flex-1">
          <div className="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
        </div>
      </AppShell>
    );
  }

  const currentSegment = progress?.current_segment;
  const totalSegments = progress?.total_segments || task.total_segments;
  const readyCount = task.segments.filter((s) => s.status === "video_ready").length;

  return (
    <AppShell
      backHref="/"
      backLabel="← 返回创作"
      right={<span className="text-xs text-muted font-mono hidden sm:block">{task.id.slice(0, 8)}</span>}
    >
      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="grid lg:grid-cols-5 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <span className="gradient-text">任务进度</span>
            </h2>
            <ProgressTimeline
              status={task.status}
              progress={task.progress}
              message={task.progress_message}
              currentSegment={currentSegment}
              totalSegments={totalSegments}
            />

            {task.status === "failed" && (
              <div className="glass-card rounded-xl p-4 border-red-200 dark:border-red-900/50">
                <p className="text-sm text-red-600 dark:text-red-400 mb-3 line-clamp-3">
                  {task.error_message || "生成失败"}
                </p>
                <button
                  onClick={handleRetry}
                  disabled={retrying}
                  className="btn-primary px-4 py-2 rounded-xl text-sm font-medium disabled:opacity-50"
                >
                  {retrying ? "重试中..." : "失败重试"}
                </button>
              </div>
            )}
          </div>

          <div className="lg:col-span-3 space-y-4">
            <h2 className="text-lg font-semibold">创作方案</h2>
            <div className="glass-card rounded-xl p-5 text-sm text-muted leading-relaxed">
              {(task.input_config.prompt as string) || "—"}
            </div>

            {task.output ? (
              <VideoPlayer
                videoUrl={task.output.video_url}
                durationMs={task.output.duration_ms}
              />
            ) : task.status === "composing" ? (
              <div className="glass-card rounded-2xl aspect-video flex items-center justify-center">
                <div className="text-center">
                  <div className="w-10 h-10 border-2 border-accent/30 border-t-accent rounded-full animate-spin mx-auto mb-3" />
                  <p className="text-sm text-muted">正在合成视频...</p>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        <div className="mt-10">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            分镜片段
            <span className="text-sm font-normal text-muted">
              ({readyCount}/{task.total_segments})
            </span>
          </h2>
          <SegmentGrid segments={task.segments} totalSegments={task.total_segments} />
        </div>
      </main>
    </AppShell>
  );
}
