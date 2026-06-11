"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { StatusBadge } from "@/components/StatusBadge";
import { listTasks, type Task } from "@/lib/api";

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "刚刚";
  if (diffMin < 60) return `${diffMin} 分钟前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour} 小时前`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 7) return `${diffDay} 天前`;
  return date.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
}

function TaskIcon({ status }: { status: string }) {
  if (status === "completed") {
    return (
      <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center shrink-0">
        <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      </div>
    );
  }
  if (status === "failed") {
    return (
      <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center shrink-0">
        <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </div>
    );
  }
  return (
    <div className="w-10 h-10 rounded-xl bg-accent-soft flex items-center justify-center shrink-0">
      <svg className="w-5 h-5 text-accent animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    </div>
  );
}

export default function HistoryPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "completed" | "failed" | "running">("all");

  useEffect(() => {
    listTasks()
      .then((data) => setTasks(data.items))
      .finally(() => setLoading(false));
  }, []);

  const stats = useMemo(() => {
    const completed = tasks.filter((t) => t.status === "completed").length;
    const failed = tasks.filter((t) => t.status === "failed").length;
    const running = tasks.filter((t) => !["completed", "failed", "cancelled"].includes(t.status)).length;
    return { total: tasks.length, completed, failed, running };
  }, [tasks]);

  const filtered = useMemo(() => {
    if (filter === "all") return tasks;
    if (filter === "completed") return tasks.filter((t) => t.status === "completed");
    if (filter === "failed") return tasks.filter((t) => t.status === "failed");
    return tasks.filter((t) => !["completed", "failed", "cancelled"].includes(t.status));
  }, [tasks, filter]);

  const filters = [
    { key: "all" as const, label: "全部", count: stats.total },
    { key: "running" as const, label: "进行中", count: stats.running },
    { key: "completed" as const, label: "已完成", count: stats.completed },
    { key: "failed" as const, label: "失败", count: stats.failed },
  ];

  return (
    <AppShell backHref="/" backLabel="← 返回创作" title="历史记录">
      <main className="page-fixed-720 py-6 sm:py-10">
        {/* 统计卡片 — 固定四列等宽 */}
        {!loading && tasks.length > 0 && (
          <div className="grid grid-cols-4 gap-3 mb-6 w-full">
            {[
              { label: "全部任务", value: stats.total, color: "from-[#667eea]/10 to-[#764ba2]/10" },
              { label: "进行中", value: stats.running, color: "from-blue-500/10 to-cyan-500/10" },
              { label: "已完成", value: stats.completed, color: "from-emerald-500/10 to-teal-500/10" },
              { label: "失败", value: stats.failed, color: "from-red-500/10 to-orange-500/10" },
            ].map((item) => (
              <div
                key={item.label}
                className={`panel-card p-3 sm:p-4 bg-gradient-to-br ${item.color} min-w-0`}
              >
                <p className="text-xl sm:text-2xl font-bold tabular-nums text-center">{item.value}</p>
                <p className="text-[11px] sm:text-xs text-muted mt-0.5 text-center truncate">{item.label}</p>
              </div>
            ))}
          </div>
        )}

        {/* 筛选 — 等宽按钮 */}
        {!loading && tasks.length > 0 && (
          <div className="grid grid-cols-4 gap-2 mb-5 w-full">
            {filters.map((f) => (
              <button
                key={f.key}
                type="button"
                onClick={() => setFilter(f.key)}
                className={`w-full px-2 py-2 rounded-xl text-xs font-medium transition-all truncate ${
                  filter === f.key
                    ? "btn-primary shadow-sm"
                    : "bg-card border border-border/60 text-muted hover:text-foreground hover:border-border"
                }`}
              >
                {f.label}
                <span className="ml-1 opacity-70 tabular-nums">{f.count}</span>
              </button>
            ))}
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 gap-3 w-full">
            <div className="w-9 h-9 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
            <p className="text-sm text-muted">加载历史记录…</p>
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-20 panel-card w-full">
            <div className="w-16 h-16 rounded-2xl bg-accent-soft flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-accent/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <p className="text-muted mb-1">暂无创作记录</p>
            <p className="text-xs text-muted/70 mb-5">开始你的第一个 AI 短视频创作吧</p>
            <Link href="/" className="btn-primary inline-block px-6 py-2.5 rounded-xl text-sm font-medium">
              开始创作
            </Link>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 panel-card w-full">
            <p className="text-sm text-muted">该分类下暂无任务</p>
          </div>
        ) : (
          <div className="space-y-3 w-full">
            {filtered.map((task) => {
              const isRunning = !["completed", "failed", "cancelled"].includes(task.status);
              return (
                <Link
                  key={task.id}
                  href={`/tasks/${task.id}`}
                  className="history-card panel-card block w-full h-[120px] p-4 pl-5 overflow-hidden"
                >
                  <div className="flex gap-3 h-full">
                    <TaskIcon status={task.status} />
                    <div className="flex-1 min-w-0 flex flex-col justify-between overflow-hidden">
                      <div className="flex items-start justify-between gap-2 min-w-0">
                        <div className="shrink-0">
                          <StatusBadge status={task.status} pulse={isRunning} />
                        </div>
                        <div className="text-right shrink-0 w-[108px]">
                          <p className="text-[11px] text-muted truncate">{formatRelativeTime(task.created_at)}</p>
                          <p className="text-[10px] text-muted/60 truncate">
                            {new Date(task.created_at).toLocaleString("zh-CN", {
                              month: "2-digit",
                              day: "2-digit",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </p>
                        </div>
                      </div>

                      <p className="text-sm font-medium leading-snug line-clamp-2 min-h-[2.5rem]">
                        {(task.input_config.prompt as string) || "—"}
                      </p>

                      <div className="flex items-center gap-2 text-[11px] text-muted min-w-0">
                        <span className="shrink-0 tabular-nums">
                          {task.total_segments} 段 · {task.segment_duration_sec}s/段
                        </span>
                        {isRunning && (
                          <span className="text-accent font-medium shrink-0 tabular-nums">{task.progress}%</span>
                        )}
                        {task.status === "completed" && task.output?.duration_ms && (
                          <span className="shrink-0 tabular-nums">
                            时长 {Math.floor(task.output.duration_ms / 1000)}s
                          </span>
                        )}
                        {isRunning && (
                          <div className="flex-1 min-w-[60px] h-1 rounded-full bg-border/50 overflow-hidden ml-auto">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-[#667eea] to-[#764ba2] transition-all duration-500"
                              style={{ width: `${task.progress}%` }}
                            />
                          </div>
                        )}
                        {task.status === "failed" && task.error_message && (
                          <span className="truncate text-red-500/80 flex-1 min-w-0">
                            {task.error_message}
                          </span>
                        )}
                      </div>
                    </div>

                    <svg
                      className="w-4 h-4 text-muted/40 shrink-0 self-center"
                      fill="none" viewBox="0 0 24 24" stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </main>
    </AppShell>
  );
}
