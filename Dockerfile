# Use the official lightweight Python image.
FROM python:3.12-slim

# Set environment variables.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user to run the app.
RUN useradd -m appuser
WORKDIR /app

# Copy only requirements first to leverage Docker cache.
COPY requirements.txt .

# Install Python dependencies.
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code.
COPY . .

# Change ownership to the non-root user.
RUN chown -R appuser:appuser /app

# Switch to non-root user.
USER appuser

# Expose the default Flask port.
EXPOSE 5000

# Set Flask environment variables (optional, can be overridden at runtime).
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Use Flask's built-in server for simplicity. In production, replace with a WSGI server like gunicorn.
CMD ["flask", "run"]