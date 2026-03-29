# Use the official lightweight Python image.
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set a working directory inside the container.
WORKDIR /app

# Install any system dependencies needed for building Python packages.
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first to leverage Docker cache.
COPY requirements.txt .

# Upgrade pip and install Python dependencies.
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn

# Copy the rest of the application code.
COPY . .

# Expose the default Flask port.
EXPOSE 5000

# Environment variables for Flask.
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Use Gunicorn as the production WSGI server.
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]