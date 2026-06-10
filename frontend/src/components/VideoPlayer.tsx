"use client";

import { resolveMediaUrl } from "@/lib/api";

interface VideoPlayerProps {
  videoUrl: string;
  durationMs?: number;
  title?: string;
}

export function VideoPlayer({ videoUrl, durationMs, title = "成品视频" }: VideoPlayerProps) {
  const src = resolveMediaUrl(videoUrl);

  const formatDuration = (ms?: number) => {
    if (!ms) return "";
    const sec = Math.floor(ms / 1000);
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      <div className="relative bg-black/5 dark:bg-black/40">
        <video
          key={src}
          src={src}
          controls
          playsInline
          preload="metadata"
          className="w-full aspect-video bg-black"
          controlsList="nodownload"
        />
        <div className="absolute top-3 left-3 px-2.5 py-1 rounded-lg bg-black/50 backdrop-blur text-white text-xs font-medium">
          AI 生成
        </div>
      </div>
      <div className="flex items-center justify-between px-5 py-4 border-t border-border/60">
        <div>
          <p className="text-sm font-semibold">{title}</p>
          {durationMs ? (
            <p className="text-xs text-muted mt-0.5">时长 {formatDuration(durationMs)}</p>
          ) : null}
        </div>
        <a
          href={src}
          download="short_video.mp4"
          className="btn-primary px-4 py-2 rounded-xl text-sm font-medium"
        >
          下载视频
        </a>
      </div>
    </div>
  );
}
