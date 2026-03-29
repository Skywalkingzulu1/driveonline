# Use an official lightweight Python image.
FROM python:3.11-slim

# Set environment variables.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory.
WORKDIR /app

# Install system dependencies (if any are needed for building Python packages).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies.
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY . .

# Expose the port Flask will run on.
EXPOSE 5000

# Set Flask environment variables.
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Run the Flask development server.
CMD ["flask", "run"]