"use client";

import { useEffect, useState } from "react";
import { getProvidersConfig, getVideoConfig, type ProvidersConfig, type VideoConfig } from "@/lib/api";

const FALLBACK_VIDEO: VideoConfig = {
  segment_count: 4,
  segment_duration_sec: 6,
  total_duration_sec: 22,
  generation_mode: "image",
  video_resolution: "768P",
  video_concurrency: 3,
  image_aspect_ratio: "16:9",
};

const FALLBACK_PROVIDERS: ProvidersConfig = {
  defaults: {
    generation_mode: "image",
    llm_provider: "minimax_llm",
    tts_provider: "minimax_tts",
    segment_provider: "minimax_image",
  },
  generation_modes: [
    { id: "image", label: "图片模式", description: "" },
    { id: "video", label: "视频模式", description: "" },
  ],
  llm_providers: [{ id: "minimax_llm", label: "MiniMax M2.5", enabled: true }],
  tts_providers: [{ id: "minimax_tts", label: "MiniMax 配音", enabled: true }],
  segment_providers: {
    image: [{
      id: "minimax_image",
      label: "MiniMax 文生图",
      enabled: true,
      capabilities: {
        max_duration_sec: 6,
        supports_first_frame: false,
        hard_cut_between_segments: true,
      },
    }],
    video: [{
      id: "minimax_hailuo",
      label: "MiniMax 海螺",
      enabled: true,
      capabilities: {
        max_duration_sec: 6,
        supports_first_frame: true,
        hard_cut_between_segments: false,
      },
    }],
  },
};

export function useGenerationConfig() {
  const [videoConfig, setVideoConfig] = useState<VideoConfig>(FALLBACK_VIDEO);
  const [providersConfig, setProvidersConfig] = useState<ProvidersConfig>(FALLBACK_PROVIDERS);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getVideoConfig(), getProvidersConfig()])
      .then(([video, providers]) => {
        setVideoConfig(video);
        setProvidersConfig(providers);
      })
      .catch(() => {
        setVideoConfig(FALLBACK_VIDEO);
        setProvidersConfig(FALLBACK_PROVIDERS);
      })
      .finally(() => setLoading(false));
  }, []);

  return { videoConfig, providersConfig, loading };
}

/** @deprecated use useGenerationConfig */
export function useVideoConfig() {
  const { videoConfig, loading } = useGenerationConfig();
  return { config: videoConfig, loading };
}
