# Backend Dockerfile for Web Notes API
FROM python:3.11-slim

# Set working directory
WORKDIR /app

RUN echo "Here we go!"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements/base.txt /app/requirements/base.txt
COPY requirements/production.txt /app/requirements/production.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements/base.txt && \
    pip install --no-cache-dir -r /app/requirements/production.txt

# Copy application code
COPY backend/ /app/backend/

# Copy alembic configuration
COPY backend/alembic.prod.ini /app/backend/

# Set working directory to backend
WORKDIR /app/backend

# Expose port (Cloud Run will set PORT env var)
ENV PORT=8080
EXPOSE $PORT

# Run database migrations and start server
CMD echo "on our way" && export ENV_FILE=env/env.prod && python -m app.main --log-level info
