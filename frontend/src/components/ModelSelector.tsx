"use client";

import clsx from "clsx";
import type { ProviderOption, ProvidersConfig } from "@/lib/api";

interface ModelSelectorProps {
  config: ProvidersConfig;
  generationMode: "image" | "video";
  onGenerationModeChange: (mode: "image" | "video") => void;
  segmentProvider: string;
  onSegmentProviderChange: (id: string) => void;
  llmProvider: string;
  onLlmProviderChange: (id: string) => void;
  ttsProvider: string;
  onTtsProviderChange: (id: string) => void;
}

export function CapabilityBadges({ provider, inline }: { provider: ProviderOption | undefined; inline?: boolean }) {
  if (!provider?.capabilities) return null;
  const caps = provider.capabilities;
  return (
    <div className={clsx("flex flex-wrap gap-1.5", inline ? "" : "mt-2")}>
      <span className="px-2 py-0.5 text-[10px] rounded-full bg-accent-soft text-accent">
        最长 {caps.max_duration_sec}s
      </span>
      {caps.supports_first_frame ? (
        <span className="px-2 py-0.5 text-[10px] rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
          首尾帧衔接
        </span>
      ) : (
        <span className="px-2 py-0.5 text-[10px] rounded-full bg-amber-50 text-amber-700 border border-amber-200">
          段间硬切
        </span>
      )}
    </div>
  );
}

export function ModelSelector({
  config,
  generationMode,
  onGenerationModeChange,
  segmentProvider,
  onSegmentProviderChange,
  llmProvider,
  onLlmProviderChange,
  ttsProvider,
  onTtsProviderChange,
}: ModelSelectorProps) {
  const segmentOptions = config.segment_providers[generationMode] ?? [];
  const selectedSegment = segmentOptions.find((p) => p.id === segmentProvider);

  return (
    <div className="space-y-4 p-1">
      <div>
        <p className="text-xs font-medium text-muted mb-2">生成模式</p>
        <div className="flex gap-2">
          {config.generation_modes.map((mode) => (
            <button
              key={mode.id}
              type="button"
              onClick={() => onGenerationModeChange(mode.id as "image" | "video")}
              className={clsx(
                "flex-1 px-3 py-2 rounded-xl text-xs font-medium border transition-colors",
                generationMode === mode.id
                  ? "border-accent bg-accent-soft text-accent"
                  : "border-border/60 text-muted hover:border-accent/40 hover:bg-accent-soft/50"
              )}
            >
              {mode.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="text-xs font-medium text-muted mb-2">分镜模型</p>
        <select
          value={segmentProvider}
          onChange={(e) => onSegmentProviderChange(e.target.value)}
          className="w-full px-3 py-2.5 rounded-xl border border-border/60 bg-[var(--card)] text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-accent/30"
        >
          {segmentOptions.map((p) => (
            <option key={p.id} value={p.id} disabled={!p.enabled}>
              {p.label}{!p.enabled ? " (未配置)" : ""}
            </option>
          ))}
        </select>
        <CapabilityBadges provider={selectedSegment} />
      </div>

      <div className="grid grid-cols-2 gap-3 pt-1 border-t border-border/40">
        <div>
          <p className="text-xs font-medium text-muted mb-2">脚本 LLM</p>
          <select
            value={llmProvider}
            onChange={(e) => onLlmProviderChange(e.target.value)}
            className="w-full px-3 py-2.5 rounded-xl border border-border/60 bg-[var(--card)] text-sm"
          >
            {config.llm_providers.map((p) => (
              <option key={p.id} value={p.id} disabled={!p.enabled}>{p.label}</option>
            ))}
          </select>
        </div>
        <div>
          <p className="text-xs font-medium text-muted mb-2">配音 TTS</p>
          <select
            value={ttsProvider}
            onChange={(e) => onTtsProviderChange(e.target.value)}
            className="w-full px-3 py-2.5 rounded-xl border border-border/60 bg-[var(--card)] text-sm"
          >
            {config.tts_providers.map((p) => (
              <option key={p.id} value={p.id} disabled={!p.enabled}>{p.label}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
