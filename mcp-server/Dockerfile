# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml .
RUN pip install --upgrade pip && pip install .

COPY src ./src

EXPOSE 8765
CMD ["python", "-m", "src.server"]
