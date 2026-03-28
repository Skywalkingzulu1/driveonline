# Use an official lightweight Python image.
FROM python:3.11-slim

# Set environment variables.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory.
WORKDIR /app

# Install system dependencies (if any) and then Python dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy the rest of the application code.
COPY . .

# Expose the port Flask will run on.
EXPOSE 5000

# Define environment variables for Flask.
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Use Gunicorn to serve the Flask app.
CMD ["gunicorn", "--workers=4", "--bind", "0.0.0.0:5000", "app:app"]