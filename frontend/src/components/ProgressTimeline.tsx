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

  return (
    <div className="glass-card rounded-2xl p-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {isCompleted && (
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          )}
          <span className="text-sm font-semibold">
            {isFailed ? "生成失败" : STATUS_LABELS[status] || status}
          </span>
        </div>
        <span className="text-sm font-mono text-muted">{progress}%</span>
      </div>

      <div className="h-2 rounded-full bg-border/60 overflow-hidden mb-5">
        <div
          className={clsx(
            "h-full rounded-full transition-all duration-700 ease-out",
            isFailed ? "bg-red-500" : "bg-gradient-to-r from-[#667eea] to-[#764ba2]"
          )}
          style={{ width: `${progress}%` }}
        />
      </div>

      {message && (
        <p className="text-sm text-muted mb-5 px-3 py-2 rounded-lg bg-accent-soft/50">{message}</p>
      )}

      <div className="space-y-0">
        {STAGE_ORDER.filter((s) => s !== "pending").map((stage, idx) => {
          const stageIdx = STAGE_ORDER.indexOf(stage);
          const isActive = !isFailed && !isCompleted && currentIdx === stageIdx;
          const isDone = isFailed ? false : isCompleted || currentIdx > stageIdx;

          let label = STATUS_LABELS[stage];
          if (stage === "segment_generating" && currentSegment && totalSegments) {
            label = `正在生成第 ${currentSegment}/${totalSegments} 个视频片段`;
          }

          return (
            <div key={stage} className="flex gap-3">
              <div className="flex flex-col items-center">
                <div
                  className={clsx(
                    "w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold transition-all",
                    isDone && "bg-gradient-to-br from-[#667eea] to-[#764ba2] text-white",
                    isActive && "ring-2 ring-accent ring-offset-2 ring-offset-card bg-accent-soft text-accent",
                    !isDone && !isActive && "bg-border/40 text-muted",
                    isFailed && stageIdx === currentIdx && "bg-red-500 text-white"
                  )}
                >
                  {isDone ? "✓" : idx + 1}
                </div>
                {idx < STAGE_ORDER.length - 2 && (
                  <div
                    className={clsx(
                      "w-0.5 flex-1 min-h-[28px] my-1 rounded-full",
                      isDone ? "bg-gradient-to-b from-[#667eea] to-[#764ba2]" : "bg-border/50"
                    )}
                  />
                )}
              </div>
              <div className="pb-5 pt-1">
                <p
                  className={clsx(
                    "text-sm",
                    isActive && "text-foreground font-medium",
                    isDone && "text-muted",
                    !isDone && !isActive && "text-muted/60"
                  )}
                >
                  {label}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
