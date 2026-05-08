"use client";

// Shows the agent path + per-node traces of the most recent /chat reply.
// During the interview demo this is the visible proof that the system
// is a multi-agent graph, not a single-call LLM wrapper.

import type { AgentName, AgentTrace } from "@/lib/types";

const AGENT_LABEL: Record<AgentName, string> = {
  supervisor: "Supervisor",
  rag: "RAG · Policy",
  sql: "Text-to-SQL",
  mcp: "MCP · Banking",
  advisor: "Advisor",
};

const AGENT_COLOR: Record<AgentName, string> = {
  supervisor: "bg-amber-500",
  rag: "bg-emerald-500",
  sql: "bg-sky-500",
  mcp: "bg-fuchsia-500",
  advisor: "bg-rose-500",
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
    <aside className="hidden lg:flex flex-col w-80 shrink-0 border-l border-zinc-800 bg-zinc-950/60 backdrop-blur p-4 overflow-y-auto">
      <div>
        <h2 className="text-sm font-semibold text-zinc-300">Agent trace</h2>
        <p className="mt-1 text-xs text-zinc-500">
          ดูเส้นทางการตัดสินใจของ multi-agent graph
        </p>
      </div>

      {path.length === 0 ? (
        <div className="mt-6 rounded-lg border border-dashed border-zinc-800 p-4 text-xs text-zinc-500">
          ยังไม่มี trace — ส่งคำถามเพื่อดูเส้นทาง agent
        </div>
      ) : (
        <>
          <div className="mt-4">
            <div className="flex items-center gap-1 flex-wrap">
              <Badge label="supervisor" color={AGENT_COLOR.supervisor} />
              {path.map((a, i) => (
                <span key={`${a}-${i}`} className="contents">
                  <span className="text-zinc-600">→</span>
                  <Badge label={AGENT_LABEL[a]} color={AGENT_COLOR[a]} />
                </span>
              ))}
              <span className="text-zinc-600">→</span>
              <Badge label="finalize" color="bg-zinc-500" />
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {traces.map((t, i) => (
              <div
                key={`${t.agent}-${i}`}
                className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-3"
              >
                <div className="flex items-center justify-between text-xs">
                  <Badge label={AGENT_LABEL[t.agent]} color={AGENT_COLOR[t.agent]} />
                  <span className="font-mono text-zinc-400">
                    {t.latency_ms.toLocaleString()} ms
                  </span>
                </div>
                <p className="mt-2 text-xs text-zinc-300 leading-relaxed line-clamp-3 break-words">
                  {t.output}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-5 border-t border-zinc-800 pt-3 text-xs text-zinc-500 flex justify-between">
            <span>Total</span>
            <span className="font-mono text-zinc-300">
              {totalMs.toLocaleString()} ms
            </span>
          </div>
        </>
      )}

      <div className="mt-auto pt-6 text-[10px] text-zinc-600">
        เปิด <a href="http://localhost:4002" target="_blank" rel="noreferrer" className="underline hover:text-zinc-400">LangFuse dashboard</a> เพื่อดู timeline เต็ม + cost
      </div>
    </aside>
  );
}

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium text-zinc-50 ${color}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-white/80" />
      {label}
    </span>
  );
}
