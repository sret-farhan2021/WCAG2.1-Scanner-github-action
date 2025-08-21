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
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 and npm from nodesource
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Verify Node.js and npm versions
RUN node --version && npm --version

# Install Puppeteer and axe-core globally
# Do not set PUPPETEER_SKIP_CHROMIUM_DOWNLOAD here to ensure Chromium is downloaded
RUN npm install -g puppeteer axe-core

# Find and link the Chromium binary
RUN CHROMIUM_PATH=$(find /usr/local/lib/node_modules/puppeteer/.local-chromium -name chrome | head -n 1) && \
    if [ -n "$CHROMIUM_PATH" ]; then \
        ln -sf $CHROMIUM_PATH /usr/local/bin/chromium-browser && \
        chmod +x $CHROMIUM_PATH; \
    else \
        echo "Error: Chromium binary not found in /usr/local/lib/node_modules/puppeteer/.local-chromium"; \
        exit 1; \
    fi

# Set environment variables for Puppeteer
ENV PUPPETEER_EXECUTABLE_PATH=/usr/local/bin/chromium-browser
ENV NODE_PATH=/usr/local/lib/node_modules

# Create app directory
WORKDIR /app

# Copy scanner.py and entrypoint.sh
COPY scanner.py /usr/bin/scanner.py
COPY entrypoint.sh /entrypoint.sh

# Make entrypoint.sh executable
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
