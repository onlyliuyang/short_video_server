import Link from "next/link";

interface AppShellProps {
  children: React.ReactNode;
  backHref?: string;
  backLabel?: string;
  title?: string;
  right?: React.ReactNode;
}

export function AppShell({ children, backHref, backLabel, title, right }: AppShellProps) {
  return (
    <div className="min-h-screen ai-mesh flex flex-col">
      <header className="sticky top-0 z-50 border-b border-border/60 glass-card !rounded-none">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            {backHref ? (
              <Link href={backHref} className="text-sm text-muted hover:text-accent transition-colors">
                {backLabel || "← 返回"}
              </Link>
            ) : (
              <Link href="/" className="flex items-center gap-2.5 group">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#667eea] to-[#764ba2] flex items-center justify-center shadow-glow">
                  <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </div>
                <span className="text-base font-semibold tracking-tight">AI 短视频</span>
              </Link>
            )}
            {title && <span className="text-base font-semibold hidden sm:block">{title}</span>}
          </div>
          <div className="flex items-center gap-4">
            {right}
            {!backHref && (
              <Link href="/history" className="text-sm text-muted hover:text-accent transition-colors">
                历史记录
              </Link>
            )}
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}
