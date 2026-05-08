import type { Metadata } from "next";
import { IBM_Plex_Sans_Thai, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// Use IBM Plex Sans Thai for proper Thai rendering — Geist's Latin-only
// glyphs fall back to system fonts which renders inconsistently across
// Windows/macOS/Linux. JetBrains Mono for code blocks (SQL traces, etc.).
const sansThai = IBM_Plex_Sans_Thai({
  variable: "--font-sans",
  subsets: ["latin", "thai"],
  weight: ["300", "400", "500", "600", "700"],
});

const mono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DeepBaht · Multi-Agent AI for Thai Personal Finance",
  description:
    "ผู้ช่วย AI ด้านการเงินส่วนบุคคล รองรับภาษาไทย ทำงานร่วมกับ RAG, Text-to-SQL, MCP",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="th"
      className={`${sansThai.variable} ${mono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full bg-zinc-950 text-zinc-100">{children}</body>
    </html>
  );
}
