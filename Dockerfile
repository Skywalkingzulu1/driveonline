FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install build dependencies (if needed) and Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Expose the Flask default port
EXPOSE 5000

# Define the default command to run the Flask development server
CMD ["flask", "run"]
