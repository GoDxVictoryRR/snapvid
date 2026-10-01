# Production Dockerfile for SnapVid (Render.com / Containerized Deployment)
FROM python:3.11-slim

# Install system dependencies including FFmpeg, system fonts, and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    fonts-liberation \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source
COPY . .

# Set default deployment environment variables
ENV PORT=8000
ENV TTS_ENGINE=edge
ENV RATE_LIMIT_PER_HOUR=10
ENV MAX_CONCURRENT_JOBS=1

EXPOSE 8000

# Run SnapVid server
CMD ["python", "-m", "snapvid.server"]
