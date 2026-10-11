# ---- Stage 1: build the React frontend ----
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python backend that also serves the built frontend ----
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code + data
COPY backend/ ./backend/
COPY nutrition/ ./nutrition/
COPY models/ ./models/
COPY llm/ ./llm/
COPY data/ ./data/

# Built frontend from stage 1
COPY --from=frontend /app/frontend/dist ./frontend/dist

ENV PORT=8000
EXPOSE 8000

# Shell form so ${PORT} (set by the host, e.g. Render) is expanded.
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
