# Use an official lightweight Python image.
FROM python:3.11-slim

# Set environment variables for Python.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a working directory.
WORKDIR /app

# Install system dependencies needed for building some Python packages.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY . .

# Create a non‑root user to run the app.
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app appuser && \
    chown -R appuser:appuser /app

# Switch to the non‑root user.
USER appuser

# Set default environment variables (can be overridden at runtime).
ENV HOST=0.0.0.0
ENV PORT=8000

# Expose the port the app runs on.
EXPOSE 8000

# Use Gunicorn with Uvicorn workers for production‑ready serving.
CMD ["gunicorn", "app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--log-level", "info"]