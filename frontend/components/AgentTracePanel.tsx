"use client";

// Agent trace sidebar — shows the routing path + per-node spans of the
// most recent /chat reply. The visible proof during demo that this is a
// multi-agent graph, not a single LLM call.

import type { AgentName, AgentTrace } from "@/lib/types";

const AGENT_LABEL: Record<AgentName, string> = {
  supervisor: "Supervisor",
  rag: "RAG · Policy",
  sql: "Text-to-SQL",
  mcp: "MCP · Banking",
  advisor: "Advisor",
};

// Per-agent visual identity — chosen for accessibility on BOTH light and
// dark backgrounds (no amber/yellow which fails on dark, no pastel which
// fails on light).
const AGENT_COLOR: Record<AgentName, { dot: string; ring: string; text: string }> = {
  supervisor: {
    dot: "bg-indigo-500 dark:bg-indigo-400",
    ring: "ring-indigo-500/20 dark:ring-indigo-500/30",
    text: "text-indigo-700 dark:text-indigo-300",
  },
  rag: {
    dot: "bg-emerald-500 dark:bg-emerald-400",
    ring: "ring-emerald-500/20 dark:ring-emerald-500/30",
    text: "text-emerald-700 dark:text-emerald-300",
  },
  sql: {
    dot: "bg-cyan-500 dark:bg-cyan-400",
    ring: "ring-cyan-500/20 dark:ring-cyan-500/30",
    text: "text-cyan-700 dark:text-cyan-300",
  },
  mcp: {
    dot: "bg-violet-500 dark:bg-violet-400",
    ring: "ring-violet-500/20 dark:ring-violet-500/30",
    text: "text-violet-700 dark:text-violet-300",
  },
  advisor: {
    dot: "bg-rose-500 dark:bg-rose-400",
    ring: "ring-rose-500/20 dark:ring-rose-500/30",
    text: "text-rose-700 dark:text-rose-300",
  },
};

const FINALIZE_COLOR = {
  dot: "bg-zinc-400 dark:bg-zinc-500",
  ring: "ring-zinc-300 dark:ring-zinc-700",
  text: "text-zinc-600 dark:text-zinc-400",
};


export function AgentTracePanel({
  path,
  traces,
}: {
  path: AgentName[];
  traces: AgentTrace[];
}) {
  const totalMs = traces.reduce((s, t) => s + (t.latency_ms ?? 0), 0);

  return (
    <aside className="hidden lg:flex flex-col w-96 shrink-0 border-l border-zinc-200 dark:border-zinc-800/80 bg-zinc-50 dark:bg-zinc-950 overflow-y-auto">
      <div className="px-5 py-4 border-b border-zinc-200 dark:border-zinc-800/80">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 tracking-tight">
          Agent trace
        </h2>
        <p className="mt-0.5 text-xs text-zinc-500 leading-snug">
          เส้นทางการตัดสินใจของ multi-agent graph
        </p>
      </div>

      {path.length === 0 ? (
        <div className="m-5 rounded-xl border border-dashed border-zinc-300 dark:border-zinc-800 bg-white/50 dark:bg-zinc-900/30 px-4 py-6 text-center">
          <div className="text-2xl opacity-40">🔍</div>
          <p className="mt-2 text-xs text-zinc-500 leading-relaxed">
            ส่งคำถามเพื่อดูเส้นทาง<br />
            ของ supervisor → agents
          </p>
        </div>
      ) : (
        <>
          {/* Path chips */}
          <div className="px-5 pt-5">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500 mb-2">
              Routing
            </div>
            <div className="flex items-center gap-1.5 flex-wrap">
              <Chip color={AGENT_COLOR.supervisor} label="supervisor" />
              {path.map((a, i) => (
                <span key={`${a}-${i}`} className="contents">
                  <Arrow />
                  <Chip color={AGENT_COLOR[a]} label={AGENT_LABEL[a]} />
                </span>
              ))}
              <Arrow />
              <Chip color={FINALIZE_COLOR} label="finalize" />
            </div>
          </div>

          {/* Spans */}
          <div className="px-5 pt-5 space-y-2.5">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
              Spans
            </div>
            {traces.map((t, i) => {
              const c = AGENT_COLOR[t.agent] ?? FINALIZE_COLOR;
              return (
                <div
                  key={`${t.agent}-${i}`}
                  className={`group rounded-xl border border-zinc-200 dark:border-zinc-800/80 bg-white dark:bg-zinc-900/40 hover:bg-zinc-50 dark:hover:bg-zinc-900/70 transition-colors p-3.5 ring-1 ${c.ring} shadow-sm`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <Chip color={c} label={AGENT_LABEL[t.agent] ?? t.agent} />
                    <Latency ms={t.latency_ms} />
                  </div>
                  <p className="text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed line-clamp-3 break-words">
                    {t.output || <span className="text-zinc-400 dark:text-zinc-600 italic">(no output)</span>}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Total */}
          <div className="mx-5 mt-5 rounded-xl bg-gradient-to-br from-emerald-500/10 to-cyan-500/10 border border-emerald-500/30 px-4 py-3 flex items-center justify-between">
            <span className="text-xs text-zinc-700 dark:text-zinc-300 font-medium">Total latency</span>
            <span className="font-mono text-sm text-emerald-700 dark:text-emerald-300 font-semibold">
              {totalMs.toLocaleString()} ms
            </span>
          </div>
        </>
      )}

      {/* Footer */}
      <div className="mt-auto px-5 py-4 border-t border-zinc-200 dark:border-zinc-800/80">
        <a
          href="http://localhost:4002"
          target="_blank"
          rel="noreferrer"
          className="group flex items-center gap-2 text-[11px] text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-300 transition-colors"
        >
          <span className="text-base">📊</span>
          <span>เปิด LangFuse dashboard <span className="opacity-50 group-hover:opacity-100">→</span></span>
        </a>
      </div>
    </aside>
  );
}


function Chip({
  color,
  label,
}: {
  color: { dot: string; text: string };
  label: string;
}) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-white/80 dark:bg-zinc-900/80 border border-zinc-200 dark:border-zinc-800 px-2 py-0.5">
      <span className={`h-1.5 w-1.5 rounded-full ${color.dot}`} />
      <span className={`text-[10px] font-medium ${color.text}`}>{label}</span>
    </span>
  );
}


function Arrow() {
  return <span className="text-zinc-400 dark:text-zinc-700 text-xs">›</span>;
}


function Latency({ ms }: { ms: number }) {
  // Speed buckets: green < 1s · amber < 3s · rose > 3s
  const tone =
    ms < 1000
      ? "text-emerald-600 dark:text-emerald-400"
      : ms < 3000
        ? "text-amber-600 dark:text-amber-400"
        : "text-rose-600 dark:text-rose-400";
  return (
    <span className={`font-mono text-[10px] ${tone} tabular-nums`}>
      {ms.toLocaleString()} ms
    </span>
  );
}
