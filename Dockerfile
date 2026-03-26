# ---------- Builder Stage ----------
# Use an official lightweight Python image for building dependencies
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Install build dependencies (if any) and system packages needed for bcrypt
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies without caching to keep image small
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application source code
COPY app.py .
COPY index.html .
COPY style.css .

# ---------- Production Runtime Stage ----------
FROM python:3.12-slim AS runtime

# Set environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Create a non‑root user to run the application
RUN useradd --create-home appuser && \
    mkdir /app && chown appuser:appuser /app

WORKDIR /app

# Copy the built application from the builder stage
COPY --from=builder /app /app

# Switch to non‑root user
USER appuser

# Expose the port that uvicorn will listen on (default 80 for production)
EXPOSE 80

# Command to run the FastAPI app with uvicorn in production mode
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80", "--workers", "2"]