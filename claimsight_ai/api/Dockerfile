# claimsight_ai/api/Dockerfile
FROM python:3.11-slim

# (Optional but recommended) basic build tools & TLS certs for wheels/native deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Faster/cleaner Python installs
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Workdir matches docker-compose working_dir
WORKDIR /workspace

# Install Python deps first (leverages layer caching)
COPY requirements.txt /workspace/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm || true

# Copy the rest of the app
COPY . /workspace

# No CMD here; docker-compose supplies the uvicorn command
# (Compose runs: uvicorn claimsight_ai.api.main:app --host 0.0.0.0 --port 8000 --proxy-headers)
