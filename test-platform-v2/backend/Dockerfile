# ── Builder stage ──
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ── Runtime stage ──
FROM python:3.12-slim
WORKDIR /app

# Copy installed pip packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000
CMD ["sh", "-c", "echo '=== CamelTv Test Platform v2.6 ===' && echo 'Running database migrations...' && alembic upgrade heads && echo 'Starting application...' && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
