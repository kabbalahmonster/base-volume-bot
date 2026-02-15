# 📖 SETUP Guide

Complete installation and setup guide for the $COMPUTE Volume Bot.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation Methods](#installation-methods)
3. [First-Time Setup](#first-time-setup)
4. [Configuration](#configuration)
5. [Verification](#verification)
6. [Server Deployment](#server-deployment)
7. [Troubleshooting Setup](#troubleshooting-setup)

---

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| **Python** | 3.9 or higher |
| **RAM** | 512 MB |
| **Disk Space** | 100 MB |
| **Network** | Stable internet connection |
| **OS** | Linux, macOS, or Windows |

### Recommended for Production

| Component | Recommendation |
|-----------|----------------|
| **Server** | VPS or dedicated server |
| **RAM** | 1 GB |
| **Network** | 99.9% uptime |
| **OS** | Ubuntu 22.04 LTS or Debian 12 |

---

## Installation Methods

### Method 1: Standard Installation (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/kabbalahmonster/base-volume-bot.git
cd base-volume-bot/volume_bot

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Verify installation
python bot.py --version
```

### Method 2: Docker Installation

```bash
# Build the Docker image
docker build -t compute-bot .

# Create config directory
mkdir -p config

# Run with mounted config
docker run -d \
  --name compute-bot \
  -v $(pwd)/config:/app/config \
  --restart unless-stopped \
  compute-bot

# View logs
docker logs -f compute-bot
```

### Method 3: Automated Deploy Script

```bash
# Run the deploy script
./deploy.sh user@your-server.com

# This will:
# - Copy files to server
# - Install dependencies
# - Setup systemd service
# - Start the bot
```

---

## First-Time Setup

### Step 1: Run Setup Command

```bash
python bot.py setup
```

### Step 2: Create Encryption Password

```
🔐 Wallet Setup
═══════════════

Create encryption password (min 8 chars):
> ********

Confirm password:
> ********

✓ Password set successfully
```

**Password Requirements:**
- Minimum 8 characters
- Can include letters, numbers, symbols
- Case-sensitive
- Cannot be recovered if lost!

### Step 3: Save Your Wallet Address

```
📝 Your Trading Wallet Address
═══════════════════════════════

0xAbC123...xyz

⚠️  IMPORTANT: Fund this address before running!
• Send ETH on Base network for trading
• Recommended minimum: 0.05 ETH
• Verify address on https://basescan.org
```

**Save this address!** You'll need it to:
- Send ETH to the bot
- Monitor transactions
- Withdraw funds

### Step 4: Fund Your Wallet

Send ETH on **Base network** (not Ethereum mainnet):

1. Open your regular wallet (MetaMask, etc.)
2. Switch to Base network
3. Send ETH to your bot's address
4. Wait for confirmation (~2-5 seconds on Base)

**Recommended Funding:**

| Strategy | Amount | Cycles |
|----------|--------|--------|
| Testing | 0.01 ETH | 2-3 cycles |
| Small | 0.05 ETH | 10-15 cycles |
| Standard | 0.1 ETH | 25-30 cycles |
| Aggressive | 0.5+ ETH | 100+ cycles |

---

## Configuration

### Basic Configuration

The setup creates `bot_config.json`. Edit it to customize:

```json
{
  "chain": "base",
  "buy_amount_eth": 0.002,
  "buy_interval_minutes": 5,
  "sell_after_buys": 10,
  "slippage_percent": 2.0,
  "max_gas_gwei": 0.5,
  "min_eth_balance": 0.01,
  "dry_run": false,
  "log_level": "INFO"
}
```

### Advanced Configuration

See [CONFIGURATION.md](CONFIGURATION.md) for all options.

### Using Custom Config Path

```bash
# Use custom config file
python bot.py run --config /path/to/config.json
```

---

## Verification

### Test Your Setup

```bash
# 1. Check installation
python bot.py --help

# 2. Check wallet balance
python bot.py balance

# 3. Run dry-run test
python bot.py run --dry-run

# 4. Check logs
ls -la *.log
cat volume_bot.log
```

### Expected Output

```
🤖 $COMPUTE Volume Bot
═══════════════════════

📊 Wallet Balance
┌──────────┬────────────────┐
│ ETH      │ 0.0500 ($125)  │
│ COMPUTE  │ 0.0000 ($0)    │
└──────────┴────────────────┘

✅ All systems operational
```

---

## Server Deployment

### Option 1: Systemd Service

#### Create Service File

```bash
sudo tee /etc/systemd/system/compute-bot.service > /dev/null <<EOF
[Unit]
Description=\$COMPUTE Volume Bot
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
Environment="PYTHONUNBUFFERED=1"
Environment="PATH=$(pwd)/venv/bin:/usr/bin"
ExecStart=$(pwd)/venv/bin/python $(pwd)/bot.py run
Restart=always
RestartSec=10
StandardOutput=append:$(pwd)/bot.log
StandardError=append:$(pwd)/bot.log

[Install]
WantedBy=multi-user.target
EOF
```

#### Enable and Start

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable compute-bot

# Start service
sudo systemctl start compute-bot

# Check status
sudo systemctl status compute-bot

# View logs
sudo journalctl -u compute-bot -f
```

#### Service Commands

```bash
# Start
sudo systemctl start compute-bot

# Stop
sudo systemctl stop compute-bot

# Restart
sudo systemctl restart compute-bot

# Check status
sudo systemctl status compute-bot

# View logs
sudo journalctl -u compute-bot -n 100
sudo journalctl -u compute-bot -f
```

### Option 2: PM2 (Node.js Process Manager)

```bash
# Install PM2
npm install -g pm2

# Start bot
pm2 start "python bot.py run" --name compute-bot

# Save PM2 config
pm2 save
pm2 startup

# Monitor
pm2 logs compute-bot
pm2 monit

# Manage
pm2 restart compute-bot
pm2 stop compute-bot
pm2 delete compute-bot
```

### Option 3: Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  compute-bot:
    build: .
    container_name: compute-bot
    restart: unless-stopped
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    environment:
      - PYTHONUNBUFFERED=1
      - CONFIG_PATH=/app/config
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Run:

```bash
# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 4: Screen/Tmux (Simple)

```bash
# Using screen
screen -S compute-bot
python bot.py run
# Detach: Ctrl+A, D

# Reattach
screen -r compute-bot

# Using tmux
tmux new -s compute-bot
python bot.py run
# Detach: Ctrl+B, D

# Reattach
tmux attach -t compute-bot
```

---

## Troubleshooting Setup

### Issue: "Command not found: python"

```bash
# Try python3 instead
python3 bot.py setup

# Or check Python installation
which python3
python3 --version
```

### Issue: "Permission denied"

```bash
# Fix permissions
chmod +x bot.py
chmod +x deploy.sh

# For wallet file
chmod 600 .wallet.enc
```

### Issue: "Module not found"

```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Issue: "Failed to connect to RPC"

```bash
# Check internet connection
ping google.com

# Try different RPC
# Edit bot_config.json and change rpc_url
```

### Issue: "Wallet file not found"

```bash
# Re-run setup
python bot.py setup

# Check if file exists
ls -la .wallet.enc
```

---

## Next Steps

After successful setup:

1. ✅ [Run your first trade](../README.md#usage)
2. ✅ [Configure advanced options](CONFIGURATION.md)
3. ✅ [Set up monitoring](#server-deployment)
4. ✅ [Learn about swarm mode](../README.md#swarm-mode)

---

## Getting Help

- 📖 [FAQ](FAQ.md) - Common questions
- 🔧 [Troubleshooting](../README.md#troubleshooting) - Common issues
- 🐛 [GitHub Issues](https://github.com/kabbalahmonster/base-volume-bot/issues) - Bug reports

---

**Ready to trade! 🚀**
