import type { Metadata } from "next";
import { IBM_Plex_Sans_Thai, JetBrains_Mono } from "next/font/google";
import "./globals.css";

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

// Inline script that runs BEFORE React hydrates, so the user never sees a
// flash-of-wrong-theme. Reads localStorage; falls back to system preference.
const themeBootstrap = `
(function(){
  try {
    var saved = localStorage.getItem('theme');
    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    var dark = saved ? saved === 'dark' : prefersDark;
    if (dark) document.documentElement.classList.add('dark');
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="th"
      className={`${sansThai.variable} ${mono.variable} h-full antialiased`}
      // suppressHydrationWarning because the inline script may flip the
      // `dark` class before React mounts — that's intentional.
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootstrap }} />
      </head>
      <body className="min-h-full bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
        {children}
      </body>
    </html>
  );
}
