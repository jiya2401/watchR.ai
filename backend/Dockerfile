FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc g++ curl \
    libxml2-dev libxslt-dev \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libgbm1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Python deps (cached layer — only rebuilds if requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browsers
RUN python -m playwright install chromium 2>/dev/null || true

COPY . .

EXPOSE 8000
