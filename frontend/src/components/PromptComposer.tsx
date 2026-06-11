"use client";

import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import type { ProvidersConfig, VideoConfig } from "@/lib/api";
import { formatDuration } from "@/lib/api";
import { CapabilityBadges, ModelSelector } from "@/components/ModelSelector";

interface PromptComposerProps {
  config: VideoConfig;
  providersConfig: ProvidersConfig;
  onSubmit: (data: {
    prompt: string;
    theme?: string;
    style?: string;
    audience?: string;
    script_direction?: string;
    generation_mode?: "image" | "video";
    llm_provider?: string;
    tts_provider?: string;
    segment_provider?: string;
  }) => void;
  loading?: boolean;
}

const STYLE_PILLS = [
  { label: "科技", key: "theme" as const, icon: "💡" },
  { label: "极简", key: "style" as const, icon: "◻️" },
  { label: "年轻用户", key: "audience" as const, icon: "👥" },
];

function SubmitIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  );
}

function ModeIcon({ mode }: { mode: "image" | "video" }) {
  if (mode === "video") {
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0">
        <polygon points="5 3 19 12 5 21 5 3" />
      </svg>
    );
  }
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <circle cx="8.5" cy="8.5" r="1.5" />
      <path d="M21 15l-5-5L5 21" />
    </svg>
  );
}

export function PromptComposer({ config, providersConfig, onSubmit, loading }: PromptComposerProps) {
  const [prompt, setPrompt] = useState("");
  const [theme, setTheme] = useState("");
  const [style, setStyle] = useState("");
  const [audience, setAudience] = useState("");
  const [scriptDirection, setScriptDirection] = useState("");
  const [showMore, setShowMore] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);

  const [generationMode, setGenerationMode] = useState<"image" | "video">(
    (providersConfig.defaults.generation_mode as "image" | "video") || "image"
  );
  const [segmentProvider, setSegmentProvider] = useState(providersConfig.defaults.segment_provider);
  const [llmProvider, setLlmProvider] = useState(providersConfig.defaults.llm_provider);
  const [ttsProvider, setTtsProvider] = useState(providersConfig.defaults.tts_provider);

  useEffect(() => {
    const options = providersConfig.segment_providers[generationMode] ?? [];
    const current = options.find((p) => p.id === segmentProvider);
    if (!current || !current.enabled) {
      const first = options.find((p) => p.enabled);
      if (first) setSegmentProvider(first.id);
    }
  }, [generationMode, providersConfig, segmentProvider]);

  useEffect(() => {
    if (!showMore) return;
    const onClickOutside = (e: MouseEvent) => {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) {
        setShowMore(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [showMore]);

  const handleGenerationModeChange = (mode: "image" | "video") => {
    setGenerationMode(mode);
    const options = providersConfig.segment_providers[mode] ?? [];
    const first = options.find((p) => p.enabled);
    if (first) setSegmentProvider(first.id);
  };

  const handleSubmit = () => {
    if (!prompt.trim() || loading) return;
    onSubmit({
      prompt: prompt.trim(),
      theme: theme || undefined,
      style: style || undefined,
      audience: audience || undefined,
      script_direction: scriptDirection || undefined,
      generation_mode: generationMode,
      llm_provider: llmProvider,
      tts_provider: ttsProvider,
      segment_provider: segmentProvider,
    });
  };

  const applyTag = (key: typeof STYLE_PILLS[number]["key"], value: string) => {
    if (key === "theme") setTheme(value);
    if (key === "style") setStyle(value);
    if (key === "audience") setAudience(value);
  };

  const selectedSegment = (providersConfig.segment_providers[generationMode] ?? []).find(
    (p) => p.id === segmentProvider
  );

  const modeLabel = generationMode === "image" ? "图片模式" : "视频模式";

  return (
    <div className="w-full max-w-3xl mx-auto px-2 sm:px-0">
      {/* 主输入框 */}
      <div className="panel-card rounded-3xl overflow-visible">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="描述你想创作的短视频，或粘贴创意方案…"
          rows={6}
          className="w-full min-h-[200px] md:min-h-[220px] bg-transparent px-7 md:px-8 pt-7 md:pt-8 pb-3 text-foreground placeholder:text-muted/60 resize-none focus:outline-none text-base md:text-[17px] leading-relaxed"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
          }}
        />

        <div className="flex items-center justify-between gap-3 px-5 py-3.5 mx-3 mb-3 rounded-2xl bg-[color-mix(in_srgb,var(--background)_60%,transparent)]">
          <button
            type="button"
            onClick={() => setShowMore((v) => !v)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-full border border-border/50 text-sm text-muted hover:text-foreground hover:border-border transition-colors min-w-0"
          >
            <ModeIcon mode={generationMode} />
            <span className="truncate max-w-[200px]">{selectedSegment?.label ?? modeLabel}</span>
          </button>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!prompt.trim() || loading}
            aria-label="生成视频"
            className={clsx(
              "shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-all",
              prompt.trim() && !loading
                ? "bg-foreground text-[var(--background)] hover:opacity-90 shadow-md"
                : "bg-border/50 text-muted cursor-not-allowed"
            )}
          >
            {loading ? (
              <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : (
              <SubmitIcon />
            )}
          </button>
        </div>
      </div>

      {/* 快捷胶囊 — 输入框下方 */}
      <div className="relative flex flex-wrap items-center justify-center gap-2 mt-5" ref={moreRef}>
        <button
          type="button"
          onClick={() => handleGenerationModeChange("image")}
          className={clsx(
            "inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm border transition-all",
            generationMode === "image"
              ? "border-accent/40 bg-accent-soft text-accent font-medium"
              : "border-border/60 bg-[var(--card)] text-muted hover:border-accent/30 hover:text-foreground"
          )}
        >
          <ModeIcon mode="image" />
          图片模式
        </button>
        <button
          type="button"
          onClick={() => handleGenerationModeChange("video")}
          className={clsx(
            "inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm border transition-all",
            generationMode === "video"
              ? "border-accent/40 bg-accent-soft text-accent font-medium"
              : "border-border/60 bg-[var(--card)] text-muted hover:border-accent/30 hover:text-foreground"
          )}
        >
          <ModeIcon mode="video" />
          视频模式
        </button>

        {STYLE_PILLS.map((pill) => (
          <button
            key={pill.label}
            type="button"
            onClick={() => applyTag(pill.key, pill.label)}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm border border-border/60 bg-[var(--card)] text-muted hover:border-accent/30 hover:text-foreground transition-all"
          >
            <span className="text-base leading-none">{pill.icon}</span>
            {pill.label}
          </button>
        ))}

        <button
          type="button"
          onClick={() => setShowMore((v) => !v)}
          className={clsx(
            "inline-flex items-center gap-1 px-4 py-2 rounded-full text-sm border transition-all",
            showMore
              ? "border-accent/40 bg-accent-soft text-accent"
              : "border-border/60 bg-[var(--card)] text-muted hover:border-accent/30 hover:text-foreground"
          )}
        >
          更多
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className={clsx("transition-transform", showMore && "rotate-180")}>
            <path d="M6 9l6 6 6-6" />
          </svg>
        </button>

        {/* 更多 — 浮层面板 */}
        {showMore && (
          <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 w-[min(100%,340px)] z-20 panel-card rounded-2xl p-4 shadow-xl border border-border/80">
            <ModelSelector
              config={providersConfig}
              generationMode={generationMode}
              onGenerationModeChange={handleGenerationModeChange}
              segmentProvider={segmentProvider}
              onSegmentProviderChange={setSegmentProvider}
              llmProvider={llmProvider}
              onLlmProviderChange={setLlmProvider}
              ttsProvider={ttsProvider}
              onTtsProviderChange={setTtsProvider}
            />
            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              className="mt-3 w-full text-xs text-muted hover:text-accent transition-colors py-1"
            >
              {showAdvanced ? "收起高级选项" : "展开高级选项（主题 / 风格 / 受众）"}
            </button>
            {showAdvanced && (
              <div className="mt-3 grid grid-cols-2 gap-2 pt-3 border-t border-border/40">
                {[
                  { label: "主题", value: theme, set: setTheme },
                  { label: "风格", value: style, set: setStyle },
                  { label: "受众", value: audience, set: setAudience },
                  { label: "脚本方向", value: scriptDirection, set: setScriptDirection },
                ].map((field) => (
                  <input
                    key={field.label}
                    value={field.value}
                    onChange={(e) => field.set(e.target.value)}
                    placeholder={field.label}
                    className="px-3 py-2 rounded-xl border border-border/60 bg-[var(--background)] text-sm placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 当前配置摘要 */}
      <div className="mt-5 flex flex-col items-center gap-2">
        <CapabilityBadges provider={selectedSegment} inline />
        <p className="text-center text-xs text-muted">
          {config.segment_count}×{config.segment_duration_sec}s · 约 {formatDuration(config.total_duration_sec)} · ⌘/Ctrl+Enter 提交
        </p>
      </div>
    </div>
  );
}
