FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install build dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Build-time arguments for secrets and configuration
ARG SECRET_KEY
ARG JWT_SECRET_KEY
ARG STRIPE_SECRET_KEY
ARG DB_CONNECTION_STRING

# Set environment variables at runtime
ENV SECRET_KEY=${SECRET_KEY}
ENV JWT_SECRET_KEY=${JWT_SECRET_KEY}
ENV STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
ENV DB_CONNECTION_STRING=${DB_CONNECTION_STRING}

# Expose the port the app runs on (Flask default 8000 in CI)
EXPOSE 8000

# Use gunicorn to serve the Flask app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
