FROM python:3.12

# Environment flags
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work dir
WORKDIR /app

# Install OS build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy source code (used in prod, overridden in dev by volume)
COPY src/ /app/

# Collect staticfiles
RUN python manage.py collectstatic --noinput || true

# Create unprivileged user for runtime
RUN adduser --disabled-password --no-create-home appuser
USER appuser

# Default CMD (overridden by docker-compose in dev)
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
