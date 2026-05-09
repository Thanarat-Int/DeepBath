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

  const aria =
    status === "recording"
      ? "หยุดอัดเสียง"
      : status === "uploading"
        ? "กำลังถอดเสียง"
        : "อัดเสียงภาษาไทย";

  return (
    <>
      <button
        type="button"
        onClick={click}
        disabled={disabled || status === "uploading"}
        title={aria}
        aria-label={aria}
        className={`flex items-center justify-center h-10 w-10 rounded-xl transition-colors ${
          status === "recording"
            ? "bg-rose-500 text-white animate-pulse shadow-lg shadow-rose-500/40"
            : status === "uploading"
              ? "bg-zinc-800 text-zinc-500"
              : "bg-zinc-800 text-zinc-200 hover:bg-zinc-700 hover:text-emerald-300"
        } disabled:opacity-30 disabled:cursor-not-allowed`}
      >
        {status === "uploading" ? (
          <span className="text-sm">⏳</span>
        ) : status === "recording" ? (
          <span className="h-2.5 w-2.5 rounded-sm bg-white" />
        ) : (
          <MicIcon />
        )}
      </button>
      {error ? (
        <span className="absolute right-0 -top-7 text-[10px] text-rose-400 whitespace-nowrap">
          ⚠ {error}
        </span>
      ) : null}
    </>
  );
}


function MicIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4"
    >
      <path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 1 0 6 0V5a3 3 0 0 0-3-3z" />
      <path d="M19 10v1a7 7 0 0 1-14 0v-1" />
      <line x1="12" x2="12" y1="18" y2="22" />
    </svg>
  );
}
