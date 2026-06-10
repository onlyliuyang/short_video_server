"use client";

import { useEffect, useState } from "react";
import { getVideoConfig, type VideoConfig } from "@/lib/api";

const FALLBACK: VideoConfig = {
  segment_count: 2,
  segment_duration_sec: 6,
  total_duration_sec: 12,
  video_resolution: "1080P",
  video_concurrency: 3,
};

export function useVideoConfig() {
  const [config, setConfig] = useState<VideoConfig>(FALLBACK);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getVideoConfig()
      .then(setConfig)
      .catch(() => setConfig(FALLBACK))
      .finally(() => setLoading(false));
  }, []);

  return { config, loading };
}
