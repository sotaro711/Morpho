# syntax=docker/dockerfile:1

# ---- フロントエンド: Next.js を静的書き出し ----
FROM node:22-slim AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV NEXT_OUTPUT=export
# Turbopack はコンテナ内で Google Fonts の取得に失敗するため webpack でビルドする
RUN npx next build

# ---- バックエンド: uv で依存解決 + S4 の C++ ビルド ----
FROM python:3.14-slim AS backend-build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/ ./
# ベースイメージの Python を使う(uv によるダウンロードを禁止)
ENV UV_PYTHON=python3.14 UV_PYTHON_DOWNLOADS=never
RUN uv sync --frozen --no-group dev --no-editable

# ---- ランタイム ----
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
# Cloud Run は PORT 環境変数で待ち受けポートを指定してくる
CMD ["sh", "-c", "uvicorn s4web.presentation.app:app --host 0.0.0.0 --port ${PORT}"]
