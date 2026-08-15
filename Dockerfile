FROM node:22-alpine AS frontend
RUN corepack enable
WORKDIR /frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.6.16 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

RUN useradd --create-home app
COPY --chown=app:app backend ./backend
COPY --from=frontend --chown=app:app /frontend/dist ./static
USER app

EXPOSE 8000
CMD [".venv/bin/uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
