import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI 短视频创作 | MiniMax",
  description: "通过 MiniMax 生成 3 分钟短视频",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
