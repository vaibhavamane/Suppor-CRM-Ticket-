# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/tickets_db

# Set work directory
WORKDIR /usr/src/app

# Install system dependencies (gcc and python3-dev are needed to compile bitarray/pybloom-live on some platforms)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Command to run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
