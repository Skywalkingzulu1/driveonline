# Use an official lightweight Python image.
FROM python:3.11-slim

# Set environment variables.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory.
WORKDIR /app

# Install system dependencies (if any) and clean up.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies.
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY . .

# Expose the port FastAPI will run on.
EXPOSE 8000

# Command to run the FastAPI application with Uvicorn.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]