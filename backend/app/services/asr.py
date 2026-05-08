"""Speech-to-text via the Typhoon ASR API.

Why the **API** backend (and not local HuggingFace) by default?
  - **Zero GPU cost** — Typhoon's free tier hosts the model for us
    (100 RPM, more than enough for a demo).
  - **No 2 GB download** at container build time.
  - **Same key** as the chat API — one credential to manage.

The local backend is implemented behind the same interface for offline
demos (eg. on a flight) — flip `ASR_BACKEND=local` in `.env`. Day-2
ships only the API path; the local-fallback hook is provided but not
implemented (a 5-line `transformers.pipeline('automatic-speech-recognition')`
call will do it once we need it).
"""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


# Accepted by Typhoon ASR (wav/flac/mp3/ogg/opus). Typed conservatively to
# avoid the API's `application/octet-stream not supported` 400 error.
_MIME_BY_EXT: dict[str, str] = {
    ".wav":  "audio/wav",
    ".flac": "audio/flac",
    ".mp3":  "audio/mpeg",
    ".ogg":  "audio/ogg",
    ".opus": "audio/opus",
    ".webm": "audio/webm",       # MediaRecorder default in browsers
    ".m4a":  "audio/mp4",
}


def _guess_mime(filename: str) -> str:
    """Pick a Content-Type the Typhoon ASR API will accept."""
    ext = Path(filename).suffix.lower()
    if ext in _MIME_BY_EXT:
        return _MIME_BY_EXT[ext]
    guess, _ = mimetypes.guess_type(filename)
    return guess or "audio/wav"


@dataclass(slots=True)
class Transcription:
    """Result of an ASR call."""
    text: str
    language: str = "th"
    duration_s: float | None = None


class ASRError(RuntimeError):
    """Raised when the ASR backend fails for any reason (auth, network, decode)."""


# ─── API backend (default) ──────────────────────────────────────────────────


async def _transcribe_via_api(audio_bytes: bytes, filename: str) -> Transcription:
    """Call the OpenTyphoon ASR endpoint (OpenAI-compatible Whisper protocol)."""
    settings = get_settings()
    url = f"{settings.typhoon_base_url.rstrip('/')}/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {settings.typhoon_api_key.get_secret_value()}",
    }
    mime = _guess_mime(filename)
    files = {"file": (filename, audio_bytes, mime)}
    data = {"model": settings.asr_model_api}

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, headers=headers, files=files, data=data)

    if resp.status_code != 200:
        log.error("asr.api_error", status=resp.status_code, body=resp.text[:300])
        raise ASRError(f"Typhoon ASR returned {resp.status_code}: {resp.text[:200]}")

    payload = resp.json()
    text = (payload.get("text") or "").strip()
    if not text:
        raise ASRError("Typhoon ASR returned empty transcript")

    log.info("asr.ok", chars=len(text), backend="api")
    return Transcription(text=text, duration_s=payload.get("duration"))


# ─── Local backend (offline / sovereign deployment) ─────────────────────────


async def _transcribe_via_local(audio_bytes: bytes, filename: str) -> Transcription:
    raise NotImplementedError(
        "Local ASR backend not wired yet. "
        "Plan: load `scb10x/typhoon-asr-realtime` via "
        "transformers.pipeline('automatic-speech-recognition') in a startup hook "
        "and route this call to it. Set ASR_BACKEND=api for now."
    )


# ─── Public entry point ─────────────────────────────────────────────────────


async def transcribe(audio_bytes: bytes, filename: str = "audio.wav") -> Transcription:
    """Transcribe Thai audio to text.

    Routes to the configured backend (`api` by default). Caller is
    responsible for supplying a valid audio container (wav / mp3 / m4a /
    flac / webm — anything ffmpeg can decode).
    """
    if not audio_bytes:
        raise ASRError("audio payload is empty")

    settings = get_settings()
    if settings.asr_backend == "local":
        return await _transcribe_via_local(audio_bytes, filename)
    return await _transcribe_via_api(audio_bytes, filename)
