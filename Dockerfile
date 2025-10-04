# Dockerfile
# Stage 1: The builder stage
FROM python:3.9-slim as builder
WORKDIR /usr/src/app
RUN apt-get update && apt-get install -y git
RUN pip install --upgrade pip
COPY requirements.txt ./
RUN pip wheel --no-cache-dir --wheel-dir /usr/src/app/wheels -r requirements.txt

# Stage 2: The final runtime stage
FROM python:3.9-slim
WORKDIR /usr/src/app
COPY --from=builder /usr/src/app/wheels /wheels
RUN pip install --no-cache /wheels/*

# Copy all application source code
COPY . .

#CMD gunicorn --bind "0.0.0.0:$PORT" --workers 1 --threads 8 --timeout 0 heartbeat_time_main:app
