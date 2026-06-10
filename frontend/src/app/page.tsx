"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { PromptComposer } from "@/components/PromptComposer";
import { useVideoConfig } from "@/hooks/useVideoConfig";
import { createTask, formatDuration } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const { config, loading: configLoading } = useVideoConfig();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: Parameters<typeof createTask>[0]) => {
    setLoading(true);
    setError(null);
    try {
      const task = await createTask(data);
      router.push(`/tasks/${task.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "提交失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-12 md:py-20">
        <div className="text-center mb-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-soft text-accent text-xs font-medium mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            Powered by MiniMax AI
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
            {configLoading ? (
              "用 AI 创作短视频"
            ) : (
              <>
                用 AI 创作
                <span className="gradient-text"> {formatDuration(config.total_duration_sec)} </span>
                短视频
              </>
            )}
          </h1>
          <p className="text-muted text-lg leading-relaxed">
            输入创意方案，自动生成脚本、{config.segment_count} 段分镜与完整视频
          </p>
        </div>

        <PromptComposer config={config} onSubmit={handleSubmit} loading={loading || configLoading} />

        {error && (
          <p className="mt-4 text-sm text-red-500 bg-red-50 dark:bg-red-950/30 px-4 py-2 rounded-lg">{error}</p>
        )}

        <div className="mt-14 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl w-full">
          {[
            { step: "01", title: "描述方案", desc: "主题、风格、受众", icon: "✍️" },
            {
              step: "02",
              title: "AI 智能生成",
              desc: configLoading ? "自动制作" : `${config.segment_count} 段视频 + 配音`,
              icon: "✨",
            },
            {
              step: "03",
              title: "预览下载",
              desc: configLoading ? "MP4 成品" : `${formatDuration(config.total_duration_sec)} 高清成片`,
              icon: "🎬",
            },
          ].map((item) => (
            <div key={item.step} className="glass-card rounded-xl p-5 text-center">
              <div className="text-2xl mb-2">{item.icon}</div>
              <p className="text-[10px] text-muted uppercase tracking-wider mb-1">{item.step}</p>
              <p className="text-sm font-semibold mb-1">{item.title}</p>
              <p className="text-xs text-muted">{item.desc}</p>
            </div>
          ))}
        </div>
      </main>
    </AppShell>
  );
}
