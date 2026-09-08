import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "ジャグラー狙い台分析",
  description: "過去データに基づく説明可能な候補台ランキング"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
