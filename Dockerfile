# Stage 1: Builder
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
# Install dependencies into specific virtualenv
# --frozen: sync exactly from lockfile
# --no-dev: exclude dev dependencies
# --no-install-project: install dependencies only, not the project itself yet
RUN uv sync --frozen --no-dev --no-install-project

# Stage 2: Runner
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies if needed (e.g. curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy virtual env from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy Application Code
# Force Cache Rebuild
ENV REBUILD_TRIGGER=v5
COPY . .

# Environment Defaults
ENV PORT=8000
ENV HOST=0.0.0.0

# Expose and Run
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
