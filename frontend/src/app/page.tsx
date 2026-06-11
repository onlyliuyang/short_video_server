"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { PromptComposer } from "@/components/PromptComposer";
import { useGenerationConfig } from "@/hooks/useGenerationConfig";
import { createTask, formatDuration } from "@/lib/api";

function generationModeHint(
  config: { segment_count: number; total_duration_sec: number },
  mode: string,
) {
  if (mode === "video") {
    return `描述创意方案，自动生成 ${config.segment_count} 段 AI 视频与完整成片`;
  }
  return `描述创意方案，自动生成 ${config.segment_count} 张分镜并合成 ${formatDuration(config.total_duration_sec)} 短视频`;
}

export default function HomePage() {
  const router = useRouter();
  const { videoConfig: config, providersConfig, loading: configLoading } = useGenerationConfig();
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
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-16 md:py-24">
        <div className="text-center mb-12 max-w-2xl">
          <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-foreground mb-3">
            想创作什么样的短视频？
          </h1>
          <p className="text-muted text-base leading-relaxed">
            {configLoading
              ? "输入创意，AI 自动生成脚本与分镜成片"
              : generationModeHint(config, providersConfig.defaults.generation_mode)}
          </p>
        </div>

        <PromptComposer
          config={config}
          providersConfig={providersConfig}
          onSubmit={handleSubmit}
          loading={loading || configLoading}
        />

        {error && (
          <p className="mt-4 text-sm text-red-500 bg-red-50 dark:bg-red-950/30 px-4 py-2 rounded-lg">{error}</p>
        )}

        <div className="mt-16 grid grid-cols-3 gap-3 max-w-3xl w-full opacity-80">
          {[
            { step: "01", title: "描述方案", icon: "✍️" },
            { step: "02", title: "AI 生成", icon: "✨" },
            { step: "03", title: "预览下载", icon: "🎬" },
          ].map((item) => (
            <div key={item.step} className="text-center py-3">
              <div className="text-xl mb-1">{item.icon}</div>
              <p className="text-[10px] text-muted uppercase tracking-wider">{item.step}</p>
              <p className="text-xs font-medium mt-0.5">{item.title}</p>
            </div>
          ))}
        </div>
      </main>
    </AppShell>
  );
}
