# Use an official Python slim image as a base for a smaller image size
FROM python:3.9-slim-bullseye

# Set best practices environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create a non-root user for security
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser

# Create and set the working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY app.py ./

# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Set the port the application will listen on (Cloud Run provides this)
ENV PORT 8080

# Command to run the Gunicorn web server, which is a production-ready server for Flask
CMD ["gunicorn","-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8080", "--workers", "1", "app:app"]
