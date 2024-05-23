# Use the official PyTorch image with CUDA 12.1
FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

# Install additional dependencies in one layer
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Ensure pip is up to date
RUN pip install --upgrade pip

# Set working directory
WORKDIR /workspace

# Copy requirements and install dependencies using pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary application files
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
