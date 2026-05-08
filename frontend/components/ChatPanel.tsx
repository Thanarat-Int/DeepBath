"use client";

// Main conversational surface — message list + composer + voice input.
// Owns chat state because (a) it's the only consumer, (b) parent page
// can stay a thin shell without prop drilling.
//
// Messages are kept in memory only. A real product would persist them via
// the session_id; that's a Day-3+ enhancement, not interview-critical.

import { useEffect, useRef, useState } from "react";

import { AgentTracePanel } from "./AgentTracePanel";
import { VoiceButton } from "./VoiceButton";
import { postChat } from "@/lib/api";
import type { AgentName, AgentTrace, UiMessage } from "@/lib/types";

const SUGGESTED: Array<{ label: string; message: string }> = [
  { label: "💸 ค่าธรรมเนียมโอน USD", message: "ค่าธรรมเนียมโอนเงิน USD ไปต่างประเทศคิดยังไง?" },
  { label: "🍱 ใช้อาหารเดือนนี้", message: "เดือนที่แล้วใช้กับอาหารไปเท่าไหร่?" },
  { label: "💰 ดอกเบี้ย FD 12 เดือน", message: "ดอกเบี้ยฝากประจำ 12 เดือนได้กี่ %?" },
  { label: "🏦 โอน 1,500 ให้ A3001", message: "โอนเงิน 1500 บาทจากบัญชีหลักไปบัญชี A3001" },
];

function newSessionId(): string {
  // Short, readable, sortable.
  const t = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
  const r = Math.random().toString(36).slice(2, 8);
  return `web-${t}-${r}`;
}

export function ChatPanel() {
  const [sessionId] = useState(() => newSessionId());
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [latestPath, setLatestPath] = useState<AgentName[]>([]);
  const [latestTraces, setLatestTraces] = useState<AgentTrace[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new message.
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
    <div className="flex h-screen w-full">
      {/* ── Main column ─────────────────────────────────── */}
      <div className="flex flex-col flex-1 min-w-0 bg-zinc-950">
        {/* Header */}
        <header className="border-b border-zinc-800 px-6 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-zinc-100">DeepBaht</h1>
            <p className="text-xs text-zinc-500">
              Multi-Agent AI for Thai Personal Finance · session{" "}
              <span className="font-mono text-zinc-400">{sessionId}</span>
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <a
              href="http://localhost:4002"
              target="_blank"
              rel="noreferrer"
              className="text-zinc-500 hover:text-zinc-300 underline-offset-4 hover:underline"
            >
              📊 LangFuse
            </a>
            <a
              href="http://localhost:4000/docs"
              target="_blank"
              rel="noreferrer"
              className="text-zinc-500 hover:text-zinc-300 underline-offset-4 hover:underline"
            >
              🛠 API docs
            </a>
          </div>
        </header>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
          {messages.length === 0 ? <Welcome onPick={send} /> : null}
          {messages.map((m) => (
            <MessageBubble key={m.id} m={m} />
          ))}
        </div>

        {/* Composer */}
        <div className="border-t border-zinc-800 px-6 py-4 bg-zinc-950">
          <div className="flex items-end gap-3">
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
              className="flex-1 resize-none rounded-lg bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
            />
            <div className="flex flex-col gap-2 shrink-0">
              <button
                type="button"
                onClick={() => void send()}
                disabled={submitting || !input.trim()}
                className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-zinc-950 hover:bg-emerald-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? "กำลังส่ง…" : "ส่ง"}
              </button>
              <VoiceButton
                disabled={submitting}
                onTranscribed={(t) => setInput((cur) => (cur ? `${cur} ${t}` : t))}
              />
            </div>
          </div>
          <p className="mt-2 text-[11px] text-zinc-600">
            กด Enter เพื่อส่ง · Shift+Enter เพื่อขึ้นบรรทัดใหม่ · 🎤 พูดเพื่อพิมพ์
          </p>
        </div>
      </div>

      {/* ── Agent trace sidebar ─────────────────────────── */}
      <AgentTracePanel path={latestPath} traces={latestTraces} />
    </div>
  );
}

function Welcome({ onPick }: { onPick: (msg: string) => void }) {
  return (
    <div className="mx-auto max-w-2xl text-center pt-12">
      <div className="text-3xl">🐬💸</div>
      <h2 className="mt-3 text-2xl font-semibold text-zinc-100">
        สวัสดี! ผมคือ DeepBaht
      </h2>
      <p className="mt-2 text-sm text-zinc-400">
        ผู้ช่วย AI ด้านการเงินส่วนบุคคลภาษาไทย — ตอบคำถามนโยบาย, วิเคราะห์ธุรกรรม,
        และทำธุรกรรมจำลองได้ผ่าน MCP
      </p>
      <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-2">
        {SUGGESTED.map((s) => (
          <button
            key={s.label}
            onClick={() => onPick(s.message)}
            className="rounded-lg border border-zinc-800 bg-zinc-900/40 hover:bg-zinc-900 px-4 py-3 text-left text-sm text-zinc-200 transition-colors"
          >
            <div className="font-medium">{s.label}</div>
            <div className="mt-0.5 text-xs text-zinc-500 line-clamp-1">{s.message}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({ m }: { m: UiMessage }) {
  const isUser = m.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? "bg-emerald-500 text-zinc-950"
            : "bg-zinc-900 border border-zinc-800 text-zinc-100"
        } ${m.pending ? "opacity-60 italic" : ""}`}
      >
        {!isUser && m.agent_path && m.agent_path.length > 0 ? (
          <div className="mb-1 text-[10px] uppercase tracking-wide text-zinc-500">
            {m.agent_path.join(" → ")}
          </div>
        ) : null}
        {m.content}
      </div>
    </div>
  );
}
