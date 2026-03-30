# Use the official lightweight Python image.
# Alpine is small but may require extra build tools for some packages.
# Here we use Debian-slim for broader compatibility.
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
# gcc and libpq-dev are often needed for building packages like bcrypt.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user to run the app
RUN useradd -m appuser
WORKDIR /app

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Ensure the static files are accessible
# (Flask is configured to serve from the project root, so no extra steps needed)

# Expose the default Flask port
EXPOSE 5000

# Switch to non-root user
USER appuser

# Define the default command to run the Flask app.
# Using gunicorn for production readiness.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]