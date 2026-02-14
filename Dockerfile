FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py ./
COPY swarm/ ./swarm/

# Don't copy config/wallet - mount as volumes
VOLUME ["/app/config"]

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory for config files
WORKDIR /app/config

# Default command (uses bot_config.json and .bot_wallet.enc in /app/config)
CMD ["python", "/app/bot.py", "run"]
