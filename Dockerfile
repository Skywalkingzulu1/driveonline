# Use an official lightweight Python image.
FROM python:3.11-slim

# Set working directory inside the container.
WORKDIR /app

# Install application dependencies.
COPY requirements.txt .
# Install both the listed requirements and gunicorn for production serving.
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy the rest of the application code.
COPY . .

# Expose the port that the application will run on.
EXPOSE 8000

# Define environment variables (optional defaults).
ENV FLASK_APP=app.py
ENV PORT=8000

# Run the Flask app with Gunicorn (4 workers, bind to all interfaces).
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]