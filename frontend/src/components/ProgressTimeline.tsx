"use client";

import clsx from "clsx";
import { STAGE_ORDER, STATUS_LABELS } from "@/lib/api";

interface ProgressTimelineProps {
  status: string;
  progress: number;
  message?: string;
  currentSegment?: number;
  totalSegments?: number;
}

export function ProgressTimeline({
  status,
  progress,
  message,
  currentSegment,
  totalSegments,
}: ProgressTimelineProps) {
  const currentIdx = STAGE_ORDER.indexOf(status);
  const isFailed = status === "failed";
  const isCompleted = status === "completed";
  const stages = STAGE_ORDER.filter((s) => s !== "pending");

  return (
    <div className="panel-card overflow-hidden">
      {/* 环形进度 + 状态 */}
      <div className="p-5 border-b border-border/50 bg-gradient-to-br from-accent-soft/40 to-transparent">
        <div className="flex items-center gap-4">
          <div className="relative w-16 h-16 shrink-0">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="15.5" fill="none" stroke="currentColor" strokeWidth="2.5" className="text-border/50" />
              <circle
                cx="18" cy="18" r="15.5" fill="none"
                stroke="url(#progressGrad)" strokeWidth="2.5"
                strokeLinecap="round"
                strokeDasharray={`${progress} 100`}
                className="transition-all duration-700"
              />
              <defs>
                <linearGradient id="progressGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#667eea" />
                  <stop offset="100%" stopColor="#764ba2" />
                </linearGradient>
              </defs>
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-sm font-bold font-mono">
              {progress}%
            </span>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold truncate">
              {isFailed ? "生成失败" : STATUS_LABELS[status] || status}
            </p>
            {message && (
              <p className="text-xs text-muted mt-1 line-clamp-2 leading-relaxed">{message}</p>
            )}
            {!message && !isCompleted && !isFailed && (
              <p className="text-xs text-muted mt-1">AI 正在处理你的创作任务…</p>
            )}
          </div>
        </div>
      </div>

      {/* 横向步骤条（桌面） */}
      <div className="hidden sm:block px-5 py-4 border-b border-border/40">
        <div className="flex items-center">
          {stages.map((stage, idx) => {
            const stageIdx = STAGE_ORDER.indexOf(stage);
            const isActive = !isFailed && !isCompleted && currentIdx === stageIdx;
            const isDone = isFailed ? false : isCompleted || currentIdx > stageIdx;
            return (
              <div key={stage} className="flex items-center flex-1 last:flex-none">
                <div
                  className={clsx(
                    "w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 transition-all",
                    isDone && "bg-gradient-to-br from-[#667eea] to-[#764ba2] text-white shadow-sm",
                    isActive && "ring-2 ring-accent bg-white dark:bg-card text-accent scale-110",
                    !isDone && !isActive && "bg-border/30 text-muted/70",
                    isFailed && stageIdx === currentIdx && "bg-red-500 text-white"
                  )}
                  title={STATUS_LABELS[stage]}
                >
                  {isDone ? "✓" : idx + 1}
                </div>
                {idx < stages.length - 1 && (
                  <div
                    className={clsx(
                      "h-0.5 flex-1 mx-1 rounded-full",
                      isDone ? "bg-gradient-to-r from-[#667eea] to-[#764ba2]" : "bg-border/40"
                    )}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 详细步骤列表 */}
      <div className="p-4 space-y-1 max-h-[280px] overflow-y-auto">
        {stages.map((stage, idx) => {
          const stageIdx = STAGE_ORDER.indexOf(stage);
          const isActive = !isFailed && !isCompleted && currentIdx === stageIdx;
          const isDone = isFailed ? false : isCompleted || currentIdx > stageIdx;

          let label = STATUS_LABELS[stage];
          if (stage === "segment_generating" && currentSegment && totalSegments) {
            label = `生成视频片段 ${currentSegment}/${totalSegments}`;
          }

          return (
            <div
              key={stage}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors",
                isActive && "bg-accent-soft/80",
                isDone && "opacity-70"
              )}
            >
              <span
                className={clsx(
                  "w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-bold shrink-0",
                  isDone && "bg-gradient-to-br from-[#667eea] to-[#764ba2] text-white",
                  isActive && "bg-accent text-white",
                  !isDone && !isActive && "bg-border/30 text-muted",
                  isFailed && stageIdx === currentIdx && "bg-red-500 text-white"
                )}
              >
                {isDone ? "✓" : idx + 1}
              </span>
              <span
                className={clsx(
                  "text-sm flex-1",
                  isActive && "font-medium text-foreground",
                  !isActive && "text-muted"
                )}
              >
                {label}
              </span>
              {isActive && (
                <span className="flex gap-0.5">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="w-1 h-1 rounded-full bg-accent animate-bounce"
                      style={{ animationDelay: `${i * 150}ms` }}
                    />
                  ))}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
