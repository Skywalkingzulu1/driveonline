# Use the official lightweight Python image.
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable stdout/stderr flushing.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set a working directory inside the container.
WORKDIR /app

# Install system build tools needed for some Python packages.
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies.
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn

# Copy the rest of the application code.
COPY . .

# Expose the port the FastAPI app will run on.
EXPOSE 8000

# Run the application with Gunicorn using Uvicorn workers for production.
CMD ["gunicorn", "app:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "4"]