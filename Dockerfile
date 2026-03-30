# Use official Python runtime as a parent image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies required for building some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn

# Copy the rest of the application code
COPY . .

# Expose the port that gunicorn will listen on
EXPOSE 8000

# Command to run the application with gunicorn in production mode
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8000", "app:app"]
