# Use the official lightweight Python image.
FROM python:3.12-slim

# Set environment variables for Python.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Install system build dependencies (required for some Python packages).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container.
WORKDIR /app

# Install Python dependencies.
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code.
COPY . .

# Expose the port the app will run on.
EXPOSE 8000

# Use Gunicorn as the production WSGI server.
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8000", "app:app"]