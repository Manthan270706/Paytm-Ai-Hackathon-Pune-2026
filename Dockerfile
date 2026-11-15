# ==============================================================================
# OpsSaathi AI - Unified All-in-One Railway Dockerfile
# Stage 1: Build React Frontend
# ==============================================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /build

COPY apps/web/package*.json ./
RUN npm ci || npm install

COPY apps/web/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Runtime (FastAPI Backend + Static React Frontend)
# ==============================================================================
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY services/api/requirements.txt ./services/api/
RUN pip install --no-cache-dir -r ./services/api/requirements.txt

# Copy backend application
COPY services/api/ ./services/api/

# Copy compiled frontend from Stage 1 into /app/static
COPY --from=frontend-builder /build/dist ./static

# Copy seeded demo SQLite database for out-of-the-box demo readiness
COPY opssaathi_demo.db ./opssaathi_demo.db

# Configure environment variables
ENV APP_ENV=production
ENV PYTHONPATH=/app/services/api
ENV DATABASE_URL=sqlite:////app/opssaathi_demo.db
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --app-dir services/api --host 0.0.0.0 --port ${PORT:-8000}"]
