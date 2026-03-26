# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy project files into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the default HTTP port
EXPOSE 8000

# Serve the static site using Python's built‑in HTTP server
CMD ["python", "-m", "http.server", "8000"]