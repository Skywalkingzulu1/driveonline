FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if any) and Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Expose the Flask default port
EXPOSE 5000

# Use Flask's built‑in server for simplicity (replace with a production server like gunicorn for real deployments)
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]