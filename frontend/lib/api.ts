// Tiny typed fetch client — wraps the two backend endpoints we talk to.
// Direct browser → backend (CORS is allow-listed for localhost:4001 in
// backend/.env), so we don't need a Next.js Route Handler proxy.

import type { ChatResponse, TranscriptionResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";

class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(`API ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

export async function postChat(
  sessionId: string,
  message: string,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
    signal,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as ChatResponse;
}

export async function postVoiceTranscribe(
  audio: Blob,
  filename = "voice.webm",
): Promise<TranscriptionResponse> {
  const form = new FormData();
  form.append("file", audio, filename);
  const res = await fetch(`${API_URL}/voice/transcribe`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as TranscriptionResponse;
}

export { ApiError };
