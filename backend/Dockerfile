# syntax=docker/dockerfile:1.7
# ─────────────────────────────────────────────────────────────────────────────
#  DeepBaht · Backend Dockerfile (multi-stage, slim production image)
#  Uses an explicit venv at /opt/venv so the runtime stage just needs to
#  copy that one directory and prepend its bin/ to PATH — no PYTHONPATH
#  juggling, no "module not found" surprises.
# ─────────────────────────────────────────────────────────────────────────────

# ──────────────── Stage 1: build dependencies ────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# System deps for sentencepiece / torch / soundfile
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libsndfile1 \
        ffmpeg \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create an isolated virtual environment we can copy whole-cloth.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY pyproject.toml .
RUN pip install --upgrade pip && \
    pip install ".[dev]"

# ──────────────── Stage 2: runtime ───────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libsndfile1 \
        ffmpeg \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY scripts ./scripts

# Non-root user
RUN useradd --create-home --shell /bin/bash deepbaht && \
    chown -R deepbaht:deepbaht /app
USER deepbaht

EXPOSE 4000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:4000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4000"]
