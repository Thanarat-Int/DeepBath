"""POST /voice/transcribe — accepts an audio file, returns Thai text.

The frontend records audio (typically webm/opus from MediaRecorder), POSTs
it here, and shoves the returned text into the /chat composer. We
deliberately keep the two endpoints separate so the user can correct
the transcript before sending it to the agents.

Limits:
  - 5 MB max upload (~30 s of speech). Real-time use cases would stream
    via websocket; left as future work.
  - Accept whatever ffmpeg/Typhoon can decode (wav/mp3/m4a/flac/webm).
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.core.logging import get_logger
from app.services.asr import ASRError, transcribe

router = APIRouter(prefix="/voice", tags=["voice"])
log = get_logger(__name__)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


class TranscriptionResponse(BaseModel):
    text: str
    duration_s: float | None = None
    language: str = "th"


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    summary="Transcribe Thai audio to text via Typhoon ASR",
)
async def voice_transcribe(file: UploadFile = File(...)) -> TranscriptionResponse:
    """Accept an audio file and return its Thai transcription."""
    audio = await file.read()
    if len(audio) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio must be ≤ {MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
        )
    if not audio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio payload",
        )

    log.info(
        "voice.transcribe.request",
        filename=file.filename,
        content_type=file.content_type,
        bytes=len(audio),
    )

    try:
        result = await transcribe(audio, filename=file.filename or "audio.wav")
    except ASRError as exc:
        log.warning("voice.transcribe.asr_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"ASR backend failed: {exc}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("voice.transcribe.error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transcription failed.",
        ) from exc

    log.info("voice.transcribe.ok", chars=len(result.text))
    return TranscriptionResponse(
        text=result.text,
        duration_s=result.duration_s,
        language=result.language,
    )
