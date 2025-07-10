FROM python:3.13-rc-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the actual Django app source from ./src
COPY src/ /app/

# Collect static files (optional depending on settings)
RUN python manage.py collectstatic --noinput || true

# Drop root user
RUN adduser --disabled-password --no-create-home appuser
USER appuser

CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
