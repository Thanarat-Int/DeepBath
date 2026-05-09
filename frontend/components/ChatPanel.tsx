"use client";

// Main conversational surface — message list + composer + voice input.
// Owns chat state because (a) it's the only consumer, (b) parent page
// can stay a thin shell without prop drilling.

import { useEffect, useRef, useState } from "react";

import { AgentTracePanel } from "./AgentTracePanel";
import { VoiceButton } from "./VoiceButton";
import { postChat } from "@/lib/api";
import type { AgentName, AgentTrace, UiMessage } from "@/lib/types";

const SUGGESTED: Array<{ icon: string; label: string; message: string; tint: string }> = [
  {
    icon: "💸",
    label: "ค่าธรรมเนียมโอน USD",
    message: "ค่าธรรมเนียมโอนเงิน USD ไปต่างประเทศคิดยังไง?",
    tint: "from-emerald-500/10 to-emerald-500/0 hover:from-emerald-500/20",
  },
  {
    icon: "🍱",
    label: "ใช้อาหารเดือนนี้",
    message: "เดือนที่แล้วใช้กับอาหารไปเท่าไหร่?",
    tint: "from-cyan-500/10 to-cyan-500/0 hover:from-cyan-500/20",
  },
  {
    icon: "💰",
    label: "ดอกเบี้ย FD 12 เดือน",
    message: "ดอกเบี้ยฝากประจำ 12 เดือนได้กี่ %?",
    tint: "from-emerald-500/10 to-emerald-500/0 hover:from-emerald-500/20",
  },
  {
    icon: "🏦",
    label: "โอน 1,500 ให้ A3001",
    message: "โอนเงิน 1500 บาทจากบัญชีหลักไปบัญชี A3001",
    tint: "from-violet-500/10 to-violet-500/0 hover:from-violet-500/20",
  },
];

const AGENT_TINT: Record<AgentName, string> = {
  supervisor: "text-indigo-300 bg-indigo-500/10 border-indigo-500/20",
  rag: "text-emerald-300 bg-emerald-500/10 border-emerald-500/20",
  sql: "text-cyan-300 bg-cyan-500/10 border-cyan-500/20",
  mcp: "text-violet-300 bg-violet-500/10 border-violet-500/20",
  advisor: "text-rose-300 bg-rose-500/10 border-rose-500/20",
};

function newSessionId(): string {
  const t = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
  const r = Math.random().toString(36).slice(2, 8);
  return `web-${t}-${r}`;
}

export function ChatPanel() {
  // sessionId is generated AFTER mount to avoid SSR/hydration mismatch.
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [latestPath, setLatestPath] = useState<AgentName[]>([]);
  const [latestTraces, setLatestTraces] = useState<AgentTrace[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSessionId(newSessionId());
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send(rawMessage?: string) {
    const message = (rawMessage ?? input).trim();
    if (!message || submitting) return;

    const userMsg: UiMessage = { id: `u-${Date.now()}`, role: "user", content: message };
    const placeholder: UiMessage = {
      id: `a-${Date.now()}`,
      role: "assistant",
      content: "กำลังคิด…",
      pending: true,
    };
    setMessages((m) => [...m, userMsg, placeholder]);
    setInput("");
    setSubmitting(true);

    try {
      const res = await postChat(sessionId, message);
      setMessages((m) =>
        m.map((x) =>
          x.id === placeholder.id
            ? {
                ...x,
                content: res.answer,
                agent_path: res.agent_path,
                traces: res.traces,
                pending: false,
              }
            : x,
        ),
      );
      setLatestPath(res.agent_path);
      setLatestTraces(res.traces);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setMessages((m) =>
        m.map((x) =>
          x.id === placeholder.id
            ? { ...x, content: `❌ ${msg}`, pending: false }
            : x,
        ),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex h-screen w-full bg-zinc-950">
      {/* ── Main column ─────────────────────────────────── */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <header className="border-b border-zinc-800/80 px-6 py-3.5 flex items-center justify-between bg-zinc-950/95 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <div className="text-2xl">🐬</div>
            <div>
              <h1 className="text-base font-semibold text-zinc-100 tracking-tight leading-none">
                DeepBaht
              </h1>
              <p className="text-[11px] text-zinc-500 mt-0.5 leading-none">
                Multi-Agent AI · Thai Personal Finance
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-zinc-600 hidden md:inline">
              {sessionId || "…"}
            </span>
            <span className="h-3 w-px bg-zinc-800 hidden md:inline-block" />
            <a
              href="http://localhost:4002"
              target="_blank"
              rel="noreferrer"
              className="text-[11px] text-zinc-400 hover:text-emerald-300 transition-colors px-2.5 py-1 rounded-md hover:bg-zinc-900"
            >
              📊 LangFuse
            </a>
            <a
              href="http://localhost:4000/docs"
              target="_blank"
              rel="noreferrer"
              className="text-[11px] text-zinc-400 hover:text-emerald-300 transition-colors px-2.5 py-1 rounded-md hover:bg-zinc-900"
            >
              🛠 API
            </a>
          </div>
        </header>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-8 space-y-5">
          {messages.length === 0 ? <Welcome onPick={send} /> : null}
          {messages.map((m) => (
            <MessageBubble key={m.id} m={m} />
          ))}
        </div>

        {/* Composer */}
        <div className="border-t border-zinc-800/80 px-6 py-4 bg-zinc-950">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-end gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/60 focus-within:border-emerald-500/50 focus-within:bg-zinc-900 transition-colors p-2.5">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void send();
                  }
                }}
                placeholder="พิมพ์คำถามภาษาไทย เช่น 'ใช้อาหารเดือนนี้เท่าไหร่?'"
                rows={2}
                className="flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none"
              />
              <div className="flex items-center gap-2 shrink-0 self-end">
                <VoiceButton
                  disabled={submitting}
                  onTranscribed={(t) => setInput((cur) => (cur ? `${cur} ${t}` : t))}
                />
                <button
                  type="button"
                  onClick={() => void send()}
                  disabled={submitting || !input.trim()}
                  className="rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-500 px-4 py-2 text-sm font-semibold text-zinc-950 hover:from-emerald-300 hover:to-emerald-400 transition-all disabled:opacity-30 disabled:cursor-not-allowed shadow-lg shadow-emerald-500/20"
                >
                  {submitting ? "…" : "ส่ง"}
                </button>
              </div>
            </div>
            <p className="mt-2 text-[10px] text-zinc-600 text-center">
              <kbd className="font-mono">Enter</kbd> ส่ง · <kbd className="font-mono">Shift+Enter</kbd> ขึ้นบรรทัดใหม่ · <kbd className="font-mono">🎤</kbd> พูดเพื่อพิมพ์
            </p>
          </div>
        </div>
      </div>

      {/* ── Agent trace sidebar ─────────────────────────── */}
      <AgentTracePanel path={latestPath} traces={latestTraces} />
    </div>
  );
}


function Welcome({ onPick }: { onPick: (msg: string) => void }) {
  return (
    <div className="mx-auto max-w-2xl text-center pt-10 pb-6">
      <div className="inline-flex items-center justify-center h-16 w-16 rounded-2xl bg-gradient-to-br from-emerald-400/20 to-cyan-500/20 border border-emerald-500/30 text-3xl mb-4">
        🐬
      </div>
      <h2 className="text-2xl font-bold text-zinc-100 tracking-tight">
        สวัสดี! ผมคือ DeepBaht
      </h2>
      <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
        ผู้ช่วย AI ด้านการเงินส่วนบุคคลภาษาไทย — ตอบคำถามนโยบาย,<br />
        วิเคราะห์ธุรกรรม, และทำธุรกรรมจำลองผ่าน MCP tools
      </p>

      <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {SUGGESTED.map((s) => (
          <button
            key={s.label}
            onClick={() => onPick(s.message)}
            className={`group rounded-xl border border-zinc-800 bg-gradient-to-br ${s.tint} hover:border-zinc-700 px-4 py-3.5 text-left transition-all`}
          >
            <div className="flex items-start gap-3">
              <div className="text-xl shrink-0 mt-0.5">{s.icon}</div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium text-zinc-100">{s.label}</div>
                <div className="mt-1 text-[11px] text-zinc-500 line-clamp-1 group-hover:text-zinc-400">
                  {s.message}
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}


function MessageBubble({ m }: { m: UiMessage }) {
  const isUser = m.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] sm:max-w-[70%] rounded-2xl rounded-tr-sm bg-gradient-to-br from-emerald-400 to-emerald-500 text-zinc-950 px-4 py-2.5 text-sm font-medium leading-relaxed whitespace-pre-wrap shadow-lg shadow-emerald-500/10">
          {m.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] sm:max-w-[78%] space-y-2">
        {m.agent_path && m.agent_path.length > 0 ? (
          <div className="flex items-center gap-1.5 text-[10px]">
            {m.agent_path.map((a, i) => (
              <span key={`${a}-${i}`} className="contents">
                {i > 0 ? <span className="text-zinc-700">›</span> : null}
                <span className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 ${AGENT_TINT[a]}`}>
                  {a}
                </span>
              </span>
            ))}
          </div>
        ) : null}
        <div
          className={`rounded-2xl rounded-tl-sm border border-zinc-800 bg-zinc-900/70 text-zinc-100 px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
            m.pending ? "opacity-60 italic" : ""
          }`}
        >
          {m.content}
        </div>
      </div>
    </div>
  );
}
