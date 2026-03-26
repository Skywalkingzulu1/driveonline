# Use the official lightweight Python image.
FROM python:3.11-slim

# Set working directory.
WORKDIR /app

# Install Python dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code.
COPY . .

# Expose the port the app will run on.
EXPOSE 80

# Use Python's built‑in HTTP server to serve the static files.
# This is sufficient for a simple static site.
CMD ["python", "-m", "http.server", "80"]