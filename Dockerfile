FROM ubuntu:latest

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Node.js dependencies globally
RUN npm install -g puppeteer axe-core

# Create symlink to ensure puppeteer is in PATH
RUN ln -sf /usr/local/lib/node_modules/puppeteer/.local-chromium/linux-*/chrome-linux/chrome /usr/local/bin/chromium-browser

# Set environment variables for Puppeteer
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=false
ENV PUPPETEER_EXECUTABLE_PATH=/usr/local/bin/chromium-browser

# Copy scanner.py and entrypoint.sh
COPY scanner.py /usr/bin/scanner.py
COPY entrypoint.sh /entrypoint.sh

# Make entrypoint.sh executable
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
