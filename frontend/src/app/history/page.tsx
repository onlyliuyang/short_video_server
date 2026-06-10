"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { listTasks, STATUS_LABELS, type Task } from "@/lib/api";

export default function HistoryPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listTasks()
      .then((data) => setTasks(data.items))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell backHref="/" backLabel="← 返回创作" title="历史记录">
      <main className="max-w-3xl mx-auto px-6 py-10">
        {loading ? (
          <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-20 glass-card rounded-2xl">
            <p className="text-muted mb-4">暂无创作记录</p>
            <Link href="/" className="btn-primary inline-block px-5 py-2 rounded-xl text-sm">
              开始创作
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map((task) => (
              <Link
                key={task.id}
                href={`/tasks/${task.id}`}
                className="block glass-card rounded-xl p-5 hover:shadow-glow transition-all hover:-translate-y-0.5"
              >
                <div className="flex items-center justify-between mb-2">
                  <span
                    className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${
                      task.status === "completed"
                        ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                        : task.status === "failed"
                          ? "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
                          : "bg-accent-soft text-accent"
                    }`}
                  >
                    {STATUS_LABELS[task.status] || task.status}
                  </span>
                  <span className="text-xs text-muted">
                    {new Date(task.created_at).toLocaleString("zh-CN")}
                  </span>
                </div>
                <p className="text-sm line-clamp-2 leading-relaxed">
                  {(task.input_config.prompt as string) || "—"}
                </p>
                {!["completed", "failed"].includes(task.status) && (
                  <div className="mt-3 h-1.5 rounded-full bg-border/60 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-[#667eea] to-[#764ba2] transition-all"
                      style={{ width: `${task.progress}%` }}
                    />
                  </div>
                )}
              </Link>
            ))}
          </div>
        )}
      </main>
    </AppShell>
  );
}
