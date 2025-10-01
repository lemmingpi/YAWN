# Backend Dockerfile for Web Notes API
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY ../requirements/base.txt /app/requirements/base.txt
COPY ../requirements/production.txt /app/requirements/production.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements/base.txt && \
    pip install --no-cache-dir -r /app/requirements/production.txt

# Copy application code
COPY . /app/backend/

# Copy alembic configuration
COPY alembic.ini /app/backend/

# Set working directory to backend
WORKDIR /app/backend

# Expose port (Cloud Run will set PORT env var)
ENV PORT=8000
EXPOSE $PORT

# Run database migrations and start server
CMD alembic upgrade head && \
    uvicorn app.main:app --host 0.0.0.0 --port $PORT
