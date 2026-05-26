# =============================================================================
# Base
# =============================================================================
FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Builder — install dependencies
# =============================================================================
FROM base AS builder

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

# =============================================================================
# Development
# =============================================================================
FROM base AS development

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# Production
# =============================================================================
FROM base AS production

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY . .

# Non-root user
RUN addgroup --system app && adduser --system --group app
USER app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# =============================================================================
# CI / Test runner
# =============================================================================
FROM base AS ci

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen

COPY . .

CMD ["pytest", "--cov=app", "--cov-report=xml", "-x"]
