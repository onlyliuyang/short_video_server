"use client";

import { useState } from "react";
import clsx from "clsx";
import type { VideoConfig } from "@/lib/api";
import { formatDuration } from "@/lib/api";

interface PromptComposerProps {
  config: VideoConfig;
  onSubmit: (data: {
    prompt: string;
    theme?: string;
    style?: string;
    audience?: string;
    script_direction?: string;
  }) => void;
  loading?: boolean;
}

const QUICK_TAGS = [
  { label: "科技", key: "theme" as const },
  { label: "极简", key: "style" as const },
  { label: "年轻用户", key: "audience" as const },
];

export function PromptComposer({ config, onSubmit, loading }: PromptComposerProps) {
  const [prompt, setPrompt] = useState("");
  const [theme, setTheme] = useState("");
  const [style, setStyle] = useState("");
  const [audience, setAudience] = useState("");
  const [scriptDirection, setScriptDirection] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = () => {
    if (!prompt.trim() || loading) return;
    onSubmit({
      prompt: prompt.trim(),
      theme: theme || undefined,
      style: style || undefined,
      audience: audience || undefined,
      script_direction: scriptDirection || undefined,
    });
  };

  const applyTag = (key: typeof QUICK_TAGS[number]["key"], value: string) => {
    if (key === "theme") setTheme(value);
    if (key === "style") setStyle(value);
    if (key === "audience") setAudience(value);
  };

  return (
    <div className="w-full max-w-3xl mx-auto">
      <div className="glass-card rounded-2xl overflow-hidden shadow-glow">
        <div className="px-5 pt-4 pb-2 flex items-center gap-2 border-b border-border/40">
          <div className="w-2 h-2 rounded-full bg-emerald-400" />
          <div className="w-2 h-2 rounded-full bg-amber-400" />
          <div className="w-2 h-2 rounded-full bg-red-400" />
          <span className="ml-2 text-xs text-muted">AI 创作助手</span>
        </div>

        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="描述你想创作的短视频。建议写明：主题 + 镜头节奏 + 风格。例如：CBD 街头从高空俯瞰到行人特写，电影感写实，段与段之间有运镜转场…"
          className="w-full min-h-[140px] bg-transparent px-6 py-5 text-foreground placeholder:text-muted/70 resize-none focus:outline-none text-base leading-relaxed"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
          }}
        />

        <div className="flex items-center justify-between px-4 py-3 border-t border-border/40 bg-accent-soft/30">
          <div className="flex items-center gap-2 flex-wrap">
            {QUICK_TAGS.map((tag) => (
              <button
                key={tag.label}
                type="button"
                onClick={() => applyTag(tag.key, tag.label)}
                className="px-3 py-1 text-xs rounded-full border border-border/60 text-muted hover:text-accent hover:border-accent/40 hover:bg-accent-soft transition-colors"
              >
                {tag.label}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="px-3 py-1 text-xs text-muted hover:text-accent transition-colors"
            >
              {showAdvanced ? "收起" : "高级选项"}
            </button>
          </div>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!prompt.trim() || loading}
            className={clsx(
              "px-5 py-2 rounded-xl text-sm font-semibold",
              prompt.trim() && !loading ? "btn-primary" : "bg-border/60 text-muted cursor-not-allowed"
            )}
          >
            {loading ? "生成中..." : "✦ 生成视频"}
          </button>
        </div>
      </div>

      {showAdvanced && (
        <div className="mt-4 grid grid-cols-2 gap-3">
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
              className="px-4 py-2.5 rounded-xl border border-border/60 glass-card text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
          ))}
        </div>
      )}

      <p className="mt-3 text-center text-xs text-muted">
        {config.segment_count}×{config.segment_duration_sec}s · 约 {formatDuration(config.total_duration_sec)} · 首尾帧衔接 · ⌘/Ctrl+Enter
      </p>
    </div>
  );
}
