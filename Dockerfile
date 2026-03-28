FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if any) and clean up
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . ./

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Expose the Flask default port
EXPOSE 5000

# Use gunicorn as the production server
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
