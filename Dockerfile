# syntax=docker/dockerfile:1

FROM node:22-slim AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV NEXT_OUTPUT=export
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
# Turbopack はコンテナ内で Google Fonts の取得に失敗するため webpack でビルドする
RUN npx next build

FROM python:3.14-slim AS backend-build
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /usr/local/bin/uv
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV UV_PYTHON=python3.14 UV_PYTHON_DOWNLOADS=never
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
COPY backend/vendor ./vendor
RUN uv sync --frozen --no-group dev --no-editable --no-install-project
COPY backend/ ./
RUN uv sync --frozen --no-group dev --no-editable

FROM python:3.14-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends libopenblas0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=backend-build /app/.venv ./.venv
COPY --from=frontend-build /build/out ./static
ENV PATH="/app/.venv/bin:$PATH" \
    S4WEB_STATIC_DIR=/app/static \
    PORT=8080
RUN useradd --system --uid 10001 --no-create-home app
USER app
# Cloud Run は PORT 環境変数で待ち受けポートを指定してくる。
# exec で uvicorn を PID 1 にし、停止時の SIGTERM を sh ではなく uvicorn が直接受け取るようにする
CMD ["sh", "-c", "exec uvicorn s4web.presentation.app:app --host 0.0.0.0 --port ${PORT}"]
