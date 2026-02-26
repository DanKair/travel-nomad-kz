# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# Frontend — Stage 1: Vite build  |  Stage 2: nginx serve
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM node:20-slim AS builder
WORKDIR /app

# Dep layer cached separately from source code
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline

COPY . .
RUN npm run build          # outputs to /app/dist

# ── Stage 2: serve ────────────────────────────────────────────────────────────
# Final image is ~25 MB (nginx:alpine) — no Node, no node_modules
FROM nginx:alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
