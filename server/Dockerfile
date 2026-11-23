# ==============================================================================
# QuoteFlow AI - Backend Dockerfile
# ==============================================================================
# Multi-purpose Python container for Django API and Celery Worker services.
# Includes Tesseract OCR, PyMuPDF, ReportLab, and PostgreSQL drivers.
# ==============================================================================

FROM python:3.11-slim-bookworm

# Prevent Python from writing bytecode (.pyc) and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install essential OS-level build tools and runtime dependencies:
# - build-essential & libpq-dev: required for compiling C extensions and psycopg2
# - tesseract-ocr & tesseract-ocr-eng: required for OCR text extraction from scanned quotes
# - curl: required for Docker container health check probes
# - netcat-traditional: required by entrypoint.sh to verify PostgreSQL port readiness
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to maximize Docker layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy entrypoint script and ensure Unix line endings and execute permissions
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copy application source code
COPY . /app/

# Create persistent storage directories for uploaded media and collected static assets
RUN mkdir -p /app/media /app/staticfiles

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
