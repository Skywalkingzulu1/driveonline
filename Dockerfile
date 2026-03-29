# Use an official lightweight Python image.
FROM python:3.11-slim

# Set environment variables for Python.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory.
WORKDIR /app

# Install system dependencies (if any are needed for building packages).
# For this project, most packages are pure Python, but we include build-essential
# to be safe for any compiled dependencies.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies.
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application source code.
COPY . .

# Set environment variables for Flask and Gunicorn.
# These can be overridden at runtime.
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PORT=8000
ENV HOST=0.0.0.0

# Expose the port that the app will run on.
EXPOSE 8000

# Use Gunicorn as the production-ready web server.
# Adjust the number of workers as needed (here we use 4 workers).
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]