# 🤖 $COMPUTE Volume Bot

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
  <img src="https://img.shields.io/badge/Base-Chain-0052FF" alt="Base Chain">
  <img src="https://img.shields.io/badge/DEX-Uniswap%20V3-FF007A" alt="Uniswap V3">
</p>

<p align="center">
  <b>Production-ready, secure Python trading bot for generating volume on Base blockchain</b>
</p>

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [CLI Commands](#-cli-commands)
- [DEX Routers](#-dex-routers)
- [Troubleshooting](#-troubleshooting)
- [Deployment](#-deployment)
- [Security](#-security)
- [Contributing](#-contributing)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔐 **Secure** | Private key encryption with PBKDF2-HMAC-SHA256 (600k iterations) |
| ⛽ **Gas Optimized** | Dynamic gas pricing with configurable limits |
| 🔄 **Multi-DEX Support** | Uniswap V3, 1inch, 0x, and Uniswap V4 routers |
| 🐝 **Swarm Mode** | Coordinate multiple wallets for volume multiplication |
| 🧪 **Dry Run Mode** | Test without spending real funds |
| 📊 **Rich CLI** | Beautiful terminal UI with progress bars and tables |
| 💰 **Auto Withdraw** | Built-in withdrawal to external wallets |
| 🛡️ **Slippage Protection** | Configurable slippage tolerance |
| 📝 **Comprehensive Logging** | File and console logging with rotation |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Volume Bot Architecture                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   CLI Layer │───→│  Bot Core   │───→│   DEX Routers       │ │
│  │  (bot.py)   │    │  (trader)   │    │ • Uniswap V3        │ │
│  └─────────────┘    └──────┬──────┘    │ • 1inch Aggregator  │ │
│                            │           │ • 0x Aggregator     │ │
│                            ↓           │ • Uniswap V4        │ │
│                     ┌─────────────┐    └─────────────────────┘ │
│                     │   Wallet    │               │            │
│                     │   Manager   │←──────────────┘            │
│                     │ (Encrypted) │                            │
│                     └─────────────┘                            │
│                            │                                    │
│                     ┌─────────────┐                            │
│                     │    Base     │                            │
│                     │  Blockchain │                            │
│                     └─────────────┘                            │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Swarm Mode (Optional)                 │   │
│  │  Queen Wallet → Funds Multiple Workers → Coordinated    │   │
│  │  Trading → Reclaim Profits                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Trading Flow

```
1. Initialize
   └─→ Load encrypted wallet
   └─→ Connect to Base network
   └─→ Validate token contracts

2. Buy Loop
   └─→ Check balances and gas
   └─→ Select best DEX router
   └─→ Execute buy transaction
   └─→ Wait for confirmation
   └─→ Track successful buys

3. Sell Trigger
   └─→ When buy count = threshold
   └─→ Execute sell transaction
   └─→ Sell all COMPUTE for ETH
   └─→ Reset buy counter

4. Repeat
   └─→ Continue buy loop
   └─→ Log all activity
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- An Ethereum wallet with ETH on Base
- (Optional) Server for 24/7 operation

### One-Line Setup

```bash
# Clone and setup
git clone https://github.com/kabbalahmonster/base-volume-bot.git
cd base-volume-bot/volume_bot
pip install -r requirements.txt
python bot.py setup
```

### Run Your First Trade

```bash
# Test mode (no real trades)
python bot.py run --dry-run

# Live trading
python bot.py run
```

---

## 📦 Installation

### Standard Installation

```bash
# 1. Clone repository
git clone https://github.com/kabbalahmonster/base-volume-bot.git
cd base-volume-bot/volume_bot

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python bot.py --help
```

### Docker Installation

```bash
# Build image
docker build -t compute-bot .

# Run with mounted config
docker run -v $(pwd)/config:/app/config compute-bot
```

### Server Deployment

```bash
# Using deploy script
./deploy.sh user@your-server.com

# Or manual deployment
scp -r volume_bot/ server:/opt/
ssh server "cd /opt/volume_bot && pip install -r requirements.txt"
```

---

## ⚙️ Configuration

### First-Time Setup

```bash
python bot.py setup
```

This will:
1. Generate a new Ethereum wallet (auto-generated)
2. Encrypt the private key with your password
3. Display your public address for funding
4. Create default configuration

### Configuration File

Edit `bot_config.json`:

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

| Setting | Description | Default |
|---------|-------------|---------|
| `buy_amount_eth` | ETH amount per buy | 0.002 (~$6) |
| `buy_interval_minutes` | Time between buys | 5 |
| `sell_after_buys` | Sell after N buys | 10 |
| `slippage_percent` | Max slippage tolerance | 2.0% |
| `max_gas_gwei` | Max gas price in Gwei | 0.5 |
| `min_eth_balance` | Minimum ETH to keep | 0.01 |

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for detailed configuration options.

---

## 🎮 Usage

### Basic Commands

```bash
# Setup wallet and config
python bot.py setup

# Run the bot
python bot.py run

# Run in test mode
python bot.py run --dry-run

# Check balances
python bot.py balance

# Withdraw funds
python bot.py withdraw <ADDRESS> --amount 0.5
```

### Swarm Mode

```bash
# Create a swarm of 10 wallets
python swarm_cli.py create --count 10

# Fund all wallets
python swarm_cli.py fund --main-key <KEY> --amount 0.02

# Start swarm trading
python swarm_cli.py run --password <PASSWORD>

# Check swarm status
python swarm_cli.py status

# Reclaim funds
python swarm_cli.py reclaim --main-address <ADDRESS> --password <PASSWORD>
```

---

## 🖥️ CLI Commands

### Main Bot Commands

```
python bot.py [COMMAND] [OPTIONS]

Commands:
  setup          Initialize encrypted wallet and configuration
  run            Start the trading bot
  balance        Display wallet balances (ETH and COMPUTE)
  withdraw       Withdraw funds to external wallet

Options:
  --dry-run      Test mode without real transactions
  --config PATH  Custom configuration file path
  --verbose, -v  Enable verbose logging
  --help         Show help message and exit
```

### Swarm CLI Commands

```
python swarm_cli.py [COMMAND] [OPTIONS]

Commands:
  create         Create new swarm wallets
  fund           Fund swarm wallets from main wallet
  run            Start swarm trading
  status         Display swarm status
  reclaim        Reclaim funds to main wallet
  logs           View swarm logs

Options:
  --count N      Number of wallets (default: 10)
  --amount ETH   Amount to fund per wallet
  --password PWD Encryption password
  --config PATH  Custom configuration file
```

---

## 🌐 DEX Routers

The bot supports multiple DEX routers for optimal pricing:

| Router | Type | Best For | Gas Cost |
|--------|------|----------|----------|
| **Uniswap V3** | AMM | Standard trades | Medium |
| **1inch** | Aggregator | Best price routing | Higher |
| **0x** | Aggregator | MEV protection | Medium |
| **Uniswap V4** | AMM | Advanced features | Lower |

See [docs/ROUTERS.md](docs/ROUTERS.md) for detailed router documentation.

---

## 🔧 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Failed to connect to RPC" | Check internet connection; bot auto-retries multiple RPCs |
| "Gas price exceeds maximum" | Increase `max_gas_gwei` in config or wait for lower gas |
| "Insufficient funds" | Ensure wallet has ETH for gas + trading |
| "Failed to decrypt wallet" | Verify password; re-run setup if needed |
| "Transaction failed" | Check gas settings and token approval |

### Viewing Logs

```bash
# Follow log file
tail -f volume_bot.log

# View last 100 lines
tail -n 100 volume_bot.log

# Search for errors
grep ERROR volume_bot.log
```

See [docs/FAQ.md](docs/FAQ.md) for more troubleshooting help.

---

## 🚀 Deployment

### Running as Systemd Service

Create `/etc/systemd/system/compute-bot.service`:

```ini
[Unit]
Description=$COMPUTE Volume Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/opt/volume_bot
Environment="PYTHONUNBUFFERED=1"
ExecStart=/opt/volume_bot/venv/bin/python bot.py run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable compute-bot
sudo systemctl start compute-bot
sudo systemctl status compute-bot
```

### Running with PM2

```bash
# Install PM2
npm install -g pm2

# Start bot
pm2 start "python bot.py run" --name compute-bot

# Monitor
pm2 logs compute-bot
pm2 monit
```

See [docs/SETUP.md](docs/SETUP.md) for complete deployment options.

---

## 🔐 Security

### Security Features

- ✅ **Auto-generated wallets** - Private key never exposed
- ✅ **PBKDF2-HMAC-SHA256 encryption** (600k iterations)
- ✅ **Random salt per wallet**
- ✅ **File permissions 600** (owner only)
- ✅ **No hardcoded secrets**
- ✅ **Secure memory handling**

### Security Checklist

Before running with real funds:

- [ ] Wallet generated and funded with ETH
- [ ] Wallet address saved for reference
- [ ] Strong encryption password (8+ chars) backed up
- [ ] Wallet file has 600 permissions
- [ ] Dry run tested successfully
- [ ] Server is secure (firewall, no malware)
- [ ] Bot running in screen/tmux or as service
- [ ] Logs being written and monitored

See [docs/SECURITY.md](docs/SECURITY.md) for complete security guidelines.

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [docs/SETUP.md](docs/SETUP.md) | Detailed installation and setup guide |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Complete configuration reference |
| [docs/ROUTERS.md](docs/ROUTERS.md) | DEX router documentation |
| [docs/FAQ.md](docs/FAQ.md) | Frequently asked questions |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | API documentation for developers |
| [docs/SWARM_GUIDE.md](docs/SWARM_GUIDE.md) | Swarm mode complete guide |
| [docs/TUTORIAL.md](docs/TUTORIAL.md) | Step-by-step tutorial |
| [docs/SECURITY.md](docs/SECURITY.md) | Security best practices |

---

## 💰 Cost Estimation

### Gas Costs (Base Network)

| Operation | Estimated Gas | Cost @ 0.1 Gwei |
|-----------|---------------|-----------------|
| Buy (ETH→Token) | ~150,000 | ~$0.0005 |
| Approve | ~50,000 | ~$0.0002 |
| Sell (Token→ETH) | ~200,000 | ~$0.0007 |
| **Per Cycle** (10 buys + 1 sell) | ~1.8M | ~$0.006 |

### Example Daily Costs

For a typical run with:
- Buy amount: 0.002 ETH (~$6)
- Buy interval: 5 minutes
- Sell after: 10 buys
- Running 24 hours:

**Daily Volume**: ~12 cycles × 10 buys × $6 = **$720 volume**  
**Daily Gas Cost**: ~12 cycles × $0.006 = **~$0.07**

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Commit with clear messages
5. Push to the branch
6. Open a Pull Request

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 🔗 Links

- **Repository**: https://github.com/kabbalahmonster/base-volume-bot
- **$COMPUTE Token**: `0x696381f39F17cAD67032f5f52A4924ce84e51BA3`
- **Base Explorer**: https://basescan.org
- **Documentation**: See `docs/` folder

---

<p align="center">
  <b>Happy Trading! 🚀</b>
</p>

<p align="center">
  <i>Built by Clawdelia for the Cult of the Shell</i> 🦑
</p>

<p align="center">
  <i>Remember: Never invest more than you can afford to lose.</i>
</p>
