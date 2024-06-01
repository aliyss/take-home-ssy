
# Use a lightweight Python image
FROM python:3.11-slim

# Install necessary packages for building nsjail
RUN apt-get update && \
    apt-get install -y \
    git \
    build-essential \
    bison \
    flex \
    libprotobuf-dev \
    protobuf-compiler \
    libnl-3-dev \
    libnl-route-3-dev \
    libseccomp-dev \
    libcap-dev \
    libcrypto++-dev \
    pkg-config \
    iproute2 \
    python3-protobuf

# Clone and build nsjail
RUN git clone https://github.com/google/nsjail /opt/nsjail && \
    cd /opt/nsjail && \
    make && \
    cp nsjail /usr/local/bin/nsjail

# Clean up
RUN apt-get remove --purge -y \
    git \
    build-essential && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY requirements-nsjail.txt ./
RUN pip install --no-cache-dir -r requirements-nsjail.txt --target=/usr/lib/python3.11/site-packages/

# Create sandbox directory
RUN mkdir -p /sandbox

# Copy the application code
COPY . .

# Expose the port
EXPOSE 8080

# Run the Flask application
CMD ["python3.11", "src/app.py"]
