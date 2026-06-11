import clsx from "clsx";
import { STATUS_LABELS } from "@/lib/api";

const STATUS_STYLES: Record<string, { className: string; dot: string }> = {
  completed: {
    className: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 ring-emerald-500/20",
    dot: "bg-emerald-500",
  },
  failed: {
    className: "bg-red-500/10 text-red-600 dark:text-red-400 ring-red-500/20",
    dot: "bg-red-500",
  },
  cancelled: {
    className: "bg-zinc-500/10 text-zinc-600 ring-zinc-500/20",
    dot: "bg-zinc-400",
  },
  pending: {
    className: "bg-zinc-500/10 text-muted ring-border/40",
    dot: "bg-muted",
  },
};

const ACTIVE_STATUSES = new Set([
  "script_generating",
  "storyboard_generating",
  "segment_generating",
  "voiceover_generating",
  "composing",
]);

export function StatusBadge({ status, pulse }: { status: string; pulse?: boolean }) {
  const preset = STATUS_STYLES[status] ?? {
    className: "bg-accent-soft text-accent ring-accent/20",
    dot: "bg-accent",
  };
  const isActive = ACTIVE_STATUSES.has(status) || pulse;

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ring-1 ring-inset",
        preset.className
      )}
    >
      <span
        className={clsx(
          "w-1.5 h-1.5 rounded-full shrink-0",
          preset.dot,
          isActive && "animate-pulse"
        )}
      />
      {STATUS_LABELS[status] || status}
    </span>
  );
}
