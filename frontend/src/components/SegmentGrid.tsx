"use client";

import { useState } from "react";
import clsx from "clsx";
import type { TaskSegment } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/api";

interface SegmentGridProps {
  segments: TaskSegment[];
  totalSegments: number;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  pending: { label: "排队中", color: "border-border/60", icon: "⏳" },
  video_generating: { label: "生成中", color: "border-amber-400/50 bg-amber-50/50 dark:bg-amber-950/20", icon: "✨" },
  video_ready: { label: "已就绪", color: "border-emerald-400/40", icon: "✓" },
  failed: { label: "失败", color: "border-red-400/50 bg-red-50/30 dark:bg-red-950/20", icon: "!" },
};

export function SegmentGrid({ segments, totalSegments }: SegmentGridProps) {
  const [active, setActive] = useState<TaskSegment | null>(null);

  const items = Array.from({ length: totalSegments }, (_, i) => {
    const seg = segments.find((s) => s.segment_index === i + 1);
    return seg || ({ segment_index: i + 1, status: "pending" } as TaskSegment);
  });

  const gridClass =
    totalSegments <= 2
      ? "grid-cols-1 sm:grid-cols-2"
      : totalSegments <= 4
        ? "grid-cols-2 lg:grid-cols-4"
        : "grid-cols-2 sm:grid-cols-3 lg:grid-cols-5";

  return (
    <>
      <div className={`grid ${gridClass} gap-3`}>
        {items.map((seg) => {
          const cfg = STATUS_CONFIG[seg.status] || STATUS_CONFIG.pending;
          const videoSrc = seg.video_url ? resolveMediaUrl(seg.video_url) : null;
          const imageSrc = seg.image_url ? resolveMediaUrl(seg.image_url) : null;
          const clickable = seg.status === "video_ready" && (videoSrc || imageSrc);
          const isGenerating = seg.status === "video_generating";

          return (
            <button
              key={seg.segment_index}
              type="button"
              disabled={!clickable}
              onClick={() => clickable && setActive(seg)}
              className={clsx(
                "group panel-card overflow-hidden text-left border-2 transition-all duration-200",
                cfg.color,
                clickable && "hover:shadow-glow hover:-translate-y-1 cursor-pointer",
                !clickable && "cursor-default"
              )}
            >
              <div className="relative aspect-video bg-gradient-to-br from-accent-soft/30 via-background to-accent-soft/10">
                {videoSrc ? (
                  <video
                    src={videoSrc}
                    muted
                    playsInline
                    preload="metadata"
                    className="w-full h-full object-cover"
                    onMouseEnter={(e) => e.currentTarget.play().catch(() => {})}
                    onMouseLeave={(e) => {
                      e.currentTarget.pause();
                      e.currentTarget.currentTime = 0;
                    }}
                  />
                ) : imageSrc ? (
                  <img
                    src={imageSrc}
                    alt={`片段 ${seg.segment_index}`}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
                    {isGenerating ? (
                      <>
                        <div className="w-8 h-8 border-2 border-accent/20 border-t-accent rounded-full animate-spin" />
                        <span className="text-[10px] text-muted">AI 生成中</span>
                      </>
                    ) : (
                      <>
                        <span className="text-2xl opacity-30">{cfg.icon}</span>
                        <span className="text-[10px] text-muted">{cfg.label}</span>
                      </>
                    )}
                  </div>
                )}

                <div className="absolute top-2 left-2 flex items-center gap-1">
                  <span className="px-2 py-0.5 rounded-md bg-black/50 backdrop-blur text-white text-[10px] font-semibold">
                    片段 {seg.segment_index}
                  </span>
                </div>

                {clickable && (
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/25 transition-opacity">
                    <div className="w-11 h-11 rounded-full bg-white/95 shadow-lg flex items-center justify-center">
                      <svg className="w-5 h-5 text-foreground ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z" />
                      </svg>
                    </div>
                  </div>
                )}
              </div>

              <div className="px-3 py-2.5 border-t border-border/40 bg-card/50">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium">{cfg.label}</span>
                  <span className="text-[10px] text-muted">{cfg.icon}</span>
                </div>
                {seg.narration_text && (
                  <p className="text-[11px] text-muted line-clamp-2 mt-1 leading-relaxed">
                    {seg.narration_text}
                  </p>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {active && (active.video_url || active.image_url) && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md"
          onClick={() => setActive(null)}
        >
          <div
            className="panel-card overflow-hidden w-full max-w-2xl shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-border/60 bg-accent-soft/30">
              <span className="text-sm font-semibold">片段 {active.segment_index}</span>
              <button
                type="button"
                onClick={() => setActive(null)}
                className="w-8 h-8 rounded-lg hover:bg-border/40 flex items-center justify-center text-muted hover:text-foreground transition-colors"
              >
                ✕
              </button>
            </div>
            {active.video_url ? (
              <video
                src={resolveMediaUrl(active.video_url)}
                controls
                autoPlay
                playsInline
                className="w-full aspect-video bg-black"
              />
            ) : active.image_url ? (
              <img
                src={resolveMediaUrl(active.image_url)}
                alt={`片段 ${active.segment_index}`}
                className="w-full aspect-video object-contain bg-black"
              />
            ) : null}
            {active.narration_text && (
              <p className="px-5 py-3.5 text-sm text-muted border-t border-border/60 leading-relaxed">
                {active.narration_text}
              </p>
            )}
          </div>
        </div>
      )}
    </>
  );
}
