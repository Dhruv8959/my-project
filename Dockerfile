# Use a slim Python image
FROM python:3.10-slim

# Install system dependencies required for OpenCV and Ultralytics
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
# We install the CPU version of PyTorch to keep the image size small and avoid OOM issues on Render
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Ensure the database and uploads directories exist
RUN mkdir -p uploads outputs

# The port is dynamically assigned by Render via the PORT environment variable
# We use 8000 as a default for local testing
ENV PORT=8000

# Start the application
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
