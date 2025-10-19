# Dockerfile

# ==============================================================================
# Stage 1: The "Builder" Stage (Unchanged)
# ==============================================================================
FROM python:3.9-slim as builder

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
COPY requirements.txt ./
RUN . /opt/venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ==============================================================================
# Stage 2: The Final "Runtime" Stage (Distroless)
# ==============================================================================
FROM gcr.io/distroless/python3-debian11

WORKDIR /app

COPY --from=builder /opt/venv/lib/python3.9/site-packages /usr/lib/python3.9/site-packages

# --- FIX: Explicitly add site-packages to PYTHONPATH ---
ENV PYTHONPATH=/usr/lib/python3.9/site-packages

# Copy your application source code (respects .dockerignore).
COPY . .

# Run gunicorn as a module (should find it via PYTHONPATH now)
CMD ["python3", "-m", "gunicorn", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8080", "time_react:app"]