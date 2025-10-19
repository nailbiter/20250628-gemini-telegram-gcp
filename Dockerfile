# Dockerfile

# ==============================================================================
# Stage 1: The "Builder" Stage
# ==============================================================================
FROM python:3.9-slim as builder

WORKDIR /usr/src/app

# Install git for pip
RUN apt-get update && apt-get install -y --no-install-recommends git

# Install Python dependencies directly into a target directory '/install'
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip
# --- FIX: Install packages fully into /install ---
RUN pip install --no-cache-dir -r requirements.txt --target=/install


# ==============================================================================
# Stage 2: The Final "Runtime" Stage (Distroless)
# ==============================================================================
FROM gcr.io/distroless/python3-debian11

WORKDIR /app

# --- FIX: Copy the installed packages from the builder's /install directory ---
# This copies them directly into the correct site-packages location for distroless
COPY --from=builder /install /usr/lib/python3.9/site-packages

# Copy your application source code (respects .dockerignore).
COPY . .

# No need for PYTHONPATH as packages are in the standard location now.
# ENV PYTHONPATH=/wheels

# The default command to run the application.
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8080", "time_react:app"]