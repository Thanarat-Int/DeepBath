"use client";

// Light/dark theme toggle. Persists choice in localStorage and applies the
// `dark` class to <html> so Tailwind's `dark:` variant kicks in everywhere.
//
// The initial theme is set BEFORE React hydrates by an inline script in
// app/layout.tsx — that's the only way to avoid a flash-of-wrong-theme
// on first paint.

import { useEffect, useState } from "react";

type Theme = "light" | "dark";

function readInitialTheme(): Theme {
  if (typeof document === "undefined") return "dark";
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("dark");

  // Sync with whatever the inline script in layout.tsx already applied.
  useEffect(() => {
    setTheme(readInitialTheme());
  }, []);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.classList.toggle("dark", next === "dark");
    try {
      localStorage.setItem("theme", next);
    } catch {
      /* private mode: ignore */
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      aria-label="Toggle theme"
      className="flex items-center justify-center h-8 w-8 rounded-lg text-zinc-500 hover:text-emerald-500 hover:bg-zinc-100 dark:hover:text-emerald-300 dark:hover:bg-zinc-900 transition-colors"
    >
      {theme === "dark" ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}


function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
    </svg>
  );
}


function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}
