FROM python:3.11-slim

# Install system dependencies
# libzbar0 is required for pyzbar
# libgl1-mesa-glx and libglib2.0-0 are required for opencv
RUN apt-get update && apt-get install -y \
    libzbar0 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for sqlite and images
RUN mkdir -p data/temp

# Set environment variables
ENV PORT=8080

# Run the application
# Using host 0.0.0.0 is crucial for Cloud Run
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
