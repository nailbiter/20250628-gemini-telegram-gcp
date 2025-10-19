# Dockerfile

# ==============================================================================
# Stage 1: The "Builder" Stage
# ==============================================================================
FROM python:3.9-slim as builder

WORKDIR /usr/src/app

# Install git for pip
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    # Clean up apt lists to reduce layer size
    rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python3 -m venv /opt/venv
# Activate venv and install requirements
COPY requirements.txt ./
RUN . /opt/venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ==============================================================================
# Stage 2: The Final "Runtime" Stage (Distroless)
# ==============================================================================
FROM gcr.io/distroless/python3-debian11

WORKDIR /app

# --- FIX: Copy packages from the virtual environment's site-packages ---
COPY --from=builder /opt/venv/lib/python3.9/site-packages /usr/lib/python3.9/site-packages

# Copy your application source code (respects .dockerignore).
COPY . .

# Run gunicorn as a module (should find it in site-packages now)
CMD ["python3", "-m", "gunicorn", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8080", "time_react:app"]