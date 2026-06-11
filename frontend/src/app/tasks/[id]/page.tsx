"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { ProgressTimeline } from "@/components/ProgressTimeline";
import { SectionHeader } from "@/components/SectionHeader";
import { SegmentGrid } from "@/components/SegmentGrid";
import { StatusBadge } from "@/components/StatusBadge";
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
        <div className="flex flex-col items-center justify-center flex-1 gap-3">
          <div className="w-10 h-10 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
          <p className="text-sm text-muted">加载任务详情…</p>
        </div>
      </AppShell>
    );
  }

  const currentSegment = progress?.current_segment;
  const totalSegments = progress?.total_segments || task.total_segments;
  const readyCount = task.segments.filter((s) => s.status === "video_ready").length;
  const prompt = (task.input_config.prompt as string) || "—";
  const isRunning = !TERMINAL_STATUSES.has(task.status);

  return (
    <AppShell
      backHref="/"
      backLabel="← 返回创作"
      right={
        <div className="flex items-center gap-3">
          <StatusBadge status={task.status} pulse={isRunning} />
          <span className="text-[11px] text-muted font-mono hidden md:block">{task.id.slice(0, 8)}</span>
        </div>
      }
    >
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* 顶部摘要 */}
        <div className="panel-card p-5 sm:p-6 mb-6 bg-gradient-to-br from-white via-white to-accent-soft/20 dark:from-card dark:via-card dark:to-accent-soft/10">
          <div className="flex flex-col sm:flex-row sm:items-start gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[#667eea] to-[#764ba2] flex items-center justify-center shrink-0 shadow-glow">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-muted mb-1">创作方案</p>
              <p className="prompt-quote text-base sm:text-lg font-medium leading-relaxed">{prompt}</p>
              <div className="flex flex-wrap gap-3 mt-4 text-xs text-muted">
                <span className="px-2.5 py-1 rounded-lg bg-accent-soft/60">{task.total_segments} 个片段</span>
                <span className="px-2.5 py-1 rounded-lg bg-accent-soft/60">每段 {task.segment_duration_sec}s</span>
                <span className="px-2.5 py-1 rounded-lg bg-accent-soft/60">
                  分镜 {readyCount}/{task.total_segments}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-12 gap-6">
          {/* 左侧进度 */}
          <div className="lg:col-span-4 xl:col-span-3">
            <SectionHeader title="任务进度" subtitle="实时跟踪生成流水线" />
            <div className="lg:sticky lg:top-24 space-y-4">
              <ProgressTimeline
                status={task.status}
                progress={task.progress}
                message={task.progress_message}
                currentSegment={currentSegment}
                totalSegments={totalSegments}
              />

              {task.status === "failed" && (
                <div className="panel-card p-4 border-red-200/80 dark:border-red-900/40 bg-red-50/50 dark:bg-red-950/20">
                  <p className="text-sm text-red-600 dark:text-red-400 mb-3 line-clamp-4 leading-relaxed">
                    {task.error_message || "生成失败，请重试"}
                  </p>
                  <button
                    onClick={handleRetry}
                    disabled={retrying}
                    className="btn-primary w-full px-4 py-2.5 rounded-xl text-sm font-medium disabled:opacity-50"
                  >
                    {retrying ? "重试中…" : "重新生成"}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* 右侧预览 */}
          <div className="lg:col-span-8 xl:col-span-9 space-y-6">
            <div>
              <SectionHeader
                title="成品预览"
                subtitle={task.output ? "生成完成，可播放或下载" : isRunning ? "视频生成完成后将在此显示" : undefined}
              />

              {task.output ? (
                <VideoPlayer
                  videoUrl={task.output.video_url}
                  durationMs={task.output.duration_ms}
                />
              ) : task.status === "composing" ? (
                <div className="panel-card aspect-video flex items-center justify-center bg-gradient-to-br from-accent-soft/20 to-transparent">
                  <div className="text-center">
                    <div className="w-12 h-12 border-2 border-accent/30 border-t-accent rounded-full animate-spin mx-auto mb-4" />
                    <p className="text-sm font-medium">正在合成最终视频</p>
                    <p className="text-xs text-muted mt-1">拼接片段、混音与字幕中…</p>
                  </div>
                </div>
              ) : (
                <div className="panel-card aspect-video flex items-center justify-center bg-gradient-to-br from-accent-soft/15 via-transparent to-accent-soft/10 border-dashed">
                  <div className="text-center px-6">
                    <div className="w-14 h-14 rounded-2xl bg-accent-soft/80 flex items-center justify-center mx-auto mb-4">
                      <svg className="w-7 h-7 text-accent/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <p className="text-sm font-medium text-muted">成品视频将在此预览</p>
                    <p className="text-xs text-muted/70 mt-1">当前进度 {task.progress}%</p>
                  </div>
                </div>
              )}
            </div>

            <div>
              <SectionHeader
                title="分镜片段"
                subtitle={`共 ${task.total_segments} 段，已完成 ${readyCount} 段`}
                badge={
                  readyCount === task.total_segments && readyCount > 0 ? (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 font-medium">
                      全部就绪
                    </span>
                  ) : isRunning ? (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600 font-medium animate-pulse">
                      生成中
                    </span>
                  ) : null
                }
              />
              <SegmentGrid segments={task.segments} totalSegments={task.total_segments} />
            </div>
          </div>
        </div>
      </main>
    </AppShell>
  );
}
