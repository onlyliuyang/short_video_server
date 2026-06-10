"use client";

import { useState } from "react";
import clsx from "clsx";
import type { TaskSegment } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/api";

interface SegmentGridProps {
  segments: TaskSegment[];
  totalSegments: number;
}

const STATUS_CONFIG: Record<string, { label: string; ring: string; dot: string }> = {
  pending: { label: "等待", ring: "ring-border", dot: "bg-muted/40" },
  video_generating: { label: "生成中", ring: "ring-amber-400/60", dot: "bg-amber-400 animate-pulse" },
  video_ready: { label: "完成", ring: "ring-emerald-400/50", dot: "bg-emerald-500" },
  failed: { label: "失败", ring: "ring-red-400/50", dot: "bg-red-500" },
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
        ? "grid-cols-2 sm:grid-cols-4"
        : "grid-cols-2 sm:grid-cols-3 md:grid-cols-5";

  return (
    <>
      <div className={`grid ${gridClass} gap-4`}>
        {items.map((seg) => {
          const cfg = STATUS_CONFIG[seg.status] || STATUS_CONFIG.pending;
          const videoSrc = seg.video_url ? resolveMediaUrl(seg.video_url) : null;
          const clickable = seg.status === "video_ready" && videoSrc;

          return (
            <button
              key={seg.segment_index}
              type="button"
              disabled={!clickable}
              onClick={() => clickable && setActive(seg)}
              className={clsx(
                "glass-card rounded-xl overflow-hidden text-left transition-all ring-2",
                cfg.ring,
                clickable && "hover:shadow-glow hover:-translate-y-0.5 cursor-pointer",
                !clickable && "cursor-default opacity-90"
              )}
            >
              <div className="relative aspect-video bg-gradient-to-br from-accent-soft to-background">
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
                ) : (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className={clsx("w-3 h-3 rounded-full", cfg.dot)} />
                  </div>
                )}
                <div className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-black/45 backdrop-blur text-white text-[10px] font-medium">
                  #{seg.segment_index}
                </div>
                {clickable && (
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 bg-black/20 transition-opacity">
                    <div className="w-10 h-10 rounded-full bg-white/90 flex items-center justify-center">
                      <svg className="w-4 h-4 text-foreground ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z" />
                      </svg>
                    </div>
                  </div>
                )}
              </div>
              <div className="px-3 py-2.5 border-t border-border/50">
                <p className="text-xs font-medium">{cfg.label}</p>
                {seg.narration_text && (
                  <p className="text-[11px] text-muted line-clamp-2 mt-0.5 leading-relaxed">
                    {seg.narration_text}
                  </p>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {active?.video_url && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
          onClick={() => setActive(null)}
        >
          <div
            className="glass-card rounded-2xl overflow-hidden w-full max-w-2xl shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-3 border-b border-border/60">
              <span className="text-sm font-semibold">片段 {active.segment_index}</span>
              <button
                type="button"
                onClick={() => setActive(null)}
                className="text-muted hover:text-foreground text-xl leading-none"
              >
                ×
              </button>
            </div>
            <video
              src={resolveMediaUrl(active.video_url)}
              controls
              autoPlay
              playsInline
              className="w-full aspect-video bg-black"
            />
            {active.narration_text && (
              <p className="px-5 py-3 text-sm text-muted border-t border-border/60">
                {active.narration_text}
              </p>
            )}
          </div>
        </div>
      )}
    </>
  );
}
