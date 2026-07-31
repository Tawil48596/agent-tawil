# ── Build stage: frontend ──
FROM node:20-alpine AS frontend-builder
WORKDIR /app/web
COPY web/package.json web/package-lock.json* ./
RUN npm ci --frozen-lockfile 2>/dev/null || npm install
COPY web/ .
RUN npm run build

# ── Runtime stage: backend ──
FROM python:3.12-slim

LABEL org.opencontainers.image.title="AI Agent Platform"
LABEL org.opencontainers.image.version="0.1.1"
LABEL org.opencontainers.image.description="通用 AI Agent 平台"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash agent
WORKDIR /home/agent/app

# Install Python dependencies
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e ".[all]"

# Copy source code
COPY --chown=agent:agent . .

# Copy frontend build
COPY --from=frontend-builder --chown=agent:agent /app/web/dist plugins/web_ui/static/

# Create data directories
RUN mkdir -p data logs chroma_data && chown -R agent:agent data logs chroma_data

USER agent
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "app.py"]
