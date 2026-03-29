# Use the official lightweight Python image
FROM python:3.12-slim

# Set environment variables to prevent Python from writing .pyc files and to enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system build dependencies (gcc is needed for some packages that require compilation)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Gunicorn (the WSGI server) separately to avoid modifying the original requirements.txt
RUN pip install --no-cache-dir gunicorn

# Copy the rest of the application code
COPY . .

# Expose the port that the application will run on
EXPOSE 8000

# Use Gunicorn to serve the Flask app in a production‑ready manner
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]