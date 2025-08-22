FROM ubuntu:latest

# Install system dependencies for Puppeteer/Chromium
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    git \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxtst6 \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1 \
    libasound2t64 \
    chromium-browser \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 and npm from nodesource
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Verify Node.js and npm versions
RUN node --version && npm --version

# Clear npm cache to avoid installation issues
RUN npm cache clean --force

# Install Puppeteer and axe-core globally, skipping Chromium download
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
RUN npm install -g puppeteer@22.12.1 axe-core

# Set environment variables for Puppeteer to use system-wide Chromium
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser
ENV NODE_PATH=/usr/local/lib/node_modules

# Create app directory
WORKDIR /app

# Copy scanner.py and entrypoint.sh
COPY scanner.py /usr/bin/scanner.py
COPY entrypoint.sh /entrypoint.sh

# Make entrypoint.sh executable
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
