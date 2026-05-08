"use client";

// Microphone button that records audio via MediaRecorder, posts it to
// /voice/transcribe, and pushes the resulting Thai text into the parent's
// composer through `onTranscribed`.
//
// Browser support: MediaRecorder + getUserMedia is available in every modern
// browser. We surface errors inline (mic permission denied, no device, etc.)
// rather than letting them disappear into the console.

import { useEffect, useRef, useState } from "react";

import { postVoiceTranscribe } from "@/lib/api";

type Status = "idle" | "recording" | "uploading" | "error";

export function VoiceButton({
  onTranscribed,
  disabled,
}: {
  onTranscribed: (text: string) => void;
  disabled?: boolean;
}) {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    return () => {
      mediaRef.current?.stream.getTracks().forEach((t) => t.stop());
    };
  }, []);

  async function startRecording() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = handleStop;
      recorder.start();
      mediaRef.current = recorder;
      setStatus("recording");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "ไม่สามารถเข้าถึงไมโครโฟน");
    }
  }

  async function handleStop() {
    setStatus("uploading");
    const recorder = mediaRef.current;
    recorder?.stream.getTracks().forEach((t) => t.stop());
    const blob = new Blob(chunksRef.current, { type: "audio/webm" });
    try {
      const result = await postVoiceTranscribe(blob, "voice.webm");
      onTranscribed(result.text);
      setStatus("idle");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "ถอดเสียงไม่สำเร็จ");
    }
  }

  function stopRecording() {
    mediaRef.current?.stop();
  }

  const click =
    status === "recording" ? stopRecording : status === "idle" ? startRecording : undefined;

  const label =
    status === "recording"
      ? "หยุดอัด"
      : status === "uploading"
        ? "กำลังถอดเสียง…"
        : "พูดเป็นภาษาไทย";

  const indicator =
    status === "recording" ? "🔴" : status === "uploading" ? "⏳" : "🎤";

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={click}
        disabled={disabled || status === "uploading"}
        title={label}
        className={`rounded-full px-3 py-2 text-sm font-medium transition-colors ${
          status === "recording"
            ? "bg-red-500 text-white animate-pulse"
            : "bg-zinc-800 text-zinc-100 hover:bg-zinc-700"
        } disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        <span className="mr-1">{indicator}</span>
        {label}
      </button>
      {error ? (
        <span className="text-xs text-red-400">⚠ {error}</span>
      ) : null}
    </div>
  );
}
