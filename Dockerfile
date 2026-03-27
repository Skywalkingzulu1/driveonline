# Use an official lightweight Python image.
FROM python:3.12-slim

# Set environment variables.
# Prevent Python from writing .pyc files and buffering stdout/stderr.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a non-root user to run the application.
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

# Set the working directory.
WORKDIR /app

# Install system dependencies required for building some Python packages.
# (e.g., gcc for building bcrypt, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code.
COPY . .

# Change ownership to the non-root user.
RUN chown -R appuser:appuser /app

# Switch to the non-root user.
USER appuser

# Expose the port that uvicorn will run on.
EXPOSE 8000

# Command to run the FastAPI application with uvicorn.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]