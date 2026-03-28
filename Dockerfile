# Use an official lightweight Python image.
FROM python:3.11-slim

# Set environment variables for Python.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a non‑root user to run the app.
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Set work directory.
WORKDIR /app

# Install system dependencies (if any) and then Python dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code.
COPY . .

# Change ownership to the non‑root user.
RUN chown -R appuser:appgroup /app

# Switch to non‑root user.
USER appuser

# Expose the default Flask port.
EXPOSE 5000

# Set Flask environment variables.
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Default command to run the Flask development server.
CMD ["flask", "run"]