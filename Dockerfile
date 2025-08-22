FROM ubuntu:latest

# Install system dependencies for Puppeteer/Chromium
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    git \
    chromium-browser \
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
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 and npm from nodesource
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Verify Node.js and npm versions
RUN node --version && npm --version

# Clear npm cache to avoid installation issues
RUN npm cache clean --force

# Create app directory
WORKDIR /app

# Install Puppeteer and axe-core locally, skipping Chromium download
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

RUN npm init -y && \
    npm install puppeteer@22.12.1 axe-core

# Verify Chromium binary
RUN ls -l /usr/bin/chromium-browser || echo "Chromium binary not found at /usr/bin/chromium-browser"

# Copy scanner.py and entrypoint.sh
COPY scanner.py /usr/bin/scanner.py
COPY entrypoint.sh /entrypoint.sh

# Make entrypoint.sh executable
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
