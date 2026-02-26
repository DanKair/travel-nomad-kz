# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Backend — UV + BuildKit cache mounts
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.13-slim

# Install uv — Rust-based pip replacement, 10-100× faster than pip
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# ── Dependency layer ──────────────────────────────────────────────────────────
# Copy requirements BEFORE source — this layer is cached unless deps change.
# --mount=type=cache reuses the uv HTTP cache across rebuilds.
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r requirements.txt

# ── Application layer ─────────────────────────────────────────────────────────
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
