FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# Cài deps trước để tận dụng cache layer
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Code + migrations
COPY backend ./backend
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

EXPOSE 8000

# Lệnh start mặc định (docker-compose.prod.yml override để chạy migration trước)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
