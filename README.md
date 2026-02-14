# 🤖 $COMPUTE Volume Bot

A production-ready, secure Python trading bot for generating volume on $COMPUTE token on Base blockchain.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Base Chain](https://img.shields.io/badge/Base-Chain-0052FF)](https://base.org)

## 📋 Features

- **🔐 Secure**: Private key encryption with PBKDF2-HMAC-SHA256 (600k iterations)
- **⛽ Gas Optimized**: Dynamic gas pricing with configurable limits
- **🔄 Retry Logic**: Exponential backoff for failed transactions
- **📊 Rich CLI**: Beautiful terminal UI with progress bars and tables
- **🧪 Dry Run Mode**: Test without spending real funds
- **💰 Withdraw**: Built-in withdrawal to external wallets
- **🛡️ Slippage Protection**: Configurable slippage tolerance
- **📝 Comprehensive Logging**: File and console logging

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- An Ethereum wallet with ETH on Base

### Installation

```bash
# Clone the repository
git clone https://github.com/kabbalahmonster/base-volume-bot.git
cd base-volume-bot/volume_bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### First-Time Setup

```bash
# Initialize encrypted wallet and config
python bot.py setup
```

The setup will:
1. **Generate a new Ethereum wallet** automatically
2. **Encrypt the private key** with your password (never displayed)
3. **Display your public address** for funding
4. **Create default configuration**

You'll be prompted for:
- Confirmation to generate a new wallet
- Encryption password (used to encrypt your key - minimum 8 characters)

This creates:
- `.wallet.enc` - Encrypted private key (permissions 600)
- `bot_config.json` - Bot configuration

#### Funding Your Wallet

After setup, you'll see your wallet address. You **must fund it** before running:

```
📝 Your Trading Wallet Address
0x... (your generated address)

⚠️  IMPORTANT: Fund this address before running the bot!
• Send ETH on Base network for trading and gas fees
• Recommended minimum: 0.05 ETH
• You can verify the address on basescan.org
```

Send ETH on Base network to this address. The bot needs ETH to:
- Execute buy transactions
- Pay for gas fees
- Have reserves for sell operations

### Configure

Edit `bot_config.json` to customize:

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

### Run the Bot

```bash
# Test in dry-run mode first
python bot.py run --dry-run

# Run live
python bot.py run
```

## 📖 Commands

| Command | Description |
|---------|-------------|
| `setup` | Initialize encrypted wallet and config |
| `run` | Start the trading bot |
| `run --dry-run` | Test mode (no real transactions) |
| `balance` | Display wallet balances |
| `withdraw <address>` | Withdraw funds to external wallet |

### Withdraw Examples

```bash
# Withdraw specific ETH amount
python bot.py withdraw 0xYourAddress --amount 0.5

# Withdraw all ETH (keeps 0.01 for gas)
python bot.py withdraw 0xYourAddress

# Withdraw ETH and all COMPUTE tokens
python bot.py withdraw 0xYourAddress --compute
```

## ⚙️ Configuration

### Default Settings (bot_config.json)

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
| `buy_amount_eth` | Amount of ETH per buy | 0.002 (~$6) |
| `buy_interval_minutes` | Minutes between buys | 5 |
| `sell_after_buys` | Sell after N buys | 10 |
| `slippage_percent` | Max slippage tolerance | 2.0% |
| `max_gas_gwei` | Max gas price in Gwei | 0.5 |
| `min_eth_balance` | Minimum ETH to keep | 0.01 |

### Security Notes

- **Auto-generated wallets** - Private key is generated locally and never exposed to user
- **Private keys are encrypted** using PBKDF2-HMAC-SHA256 with 600k iterations + random salt
- **Wallet file permissions** are set to 600 (owner read/write only)
- **Never commit** your `.wallet.enc` or `bot_config.json` to version control
- **Backup your encryption password** - without it, the private key cannot be recovered
- **Backup your wallet address** - you'll need it to send funds to the bot

## 🏗️ Architecture

```
volume_bot/
├── bot.py              # CLI entry point and main loop
├── wallet.py           # Secure key management (PBKDF2 + Fernet)
├── trader.py           # Uniswap V3 trading logic
├── swarm/              # Swarm wallet feature (optional)
│   ├── manager.py
│   └── __init__.py
├── requirements.txt    # Python dependencies
├── bot_config.json     # Bot configuration (auto-created)
├── .bot_wallet.enc     # Encrypted private key (auto-created)
└── README.md           # This file
```

### Trading Flow

1. **Initialize**: Load encrypted wallet, connect to Base
2. **Buy Loop**: Execute buys at configured intervals
3. **Count**: Track number of successful buys
4. **Sell Trigger**: When buy count reaches threshold, sell all COMPUTE
5. **Repeat**: Reset counter and continue

### Security Flow

#### Auto-Generated Wallet Creation

```
┌─────────────────┐
│  User confirms  │
│  "Generate      │
│   wallet?"      │
└────────┬────────┘
         ↓
┌─────────────────┐     ┌──────────────────┐
│  os.urandom()   │────→│  eth_account.    │
│  + secrets      │     │  Account.create()│
└─────────────────┘     └────────┬─────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  Private Key Generated  │
                    │  (never displayed)      │
                    └───────────┬─────────────┘
                                ↓
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  User Password  │───→│  PBKDF2-HMAC    │───→│  Fernet Key     │
└─────────────────┘    │  (480k iter)    │    └────────┬────────┘
                       └─────────────────┘             ↓
                                            ┌─────────────────┐
                                            │  Encrypt Key    │
                                            │  + Save to      │
                                            │  .wallet.enc    │
                                            └─────────────────┘
```

#### Runtime Decryption

```
User Password + Stored Salt
           ↓
    PBKDF2-HMAC-SHA256 (480k iterations)
           ↓
      Fernet Encryption Key
           ↓
    Decrypt Private Key → Memory (runtime only)
           ↓
    Sign Transactions → Send to Base Network
```

## 💰 Cost Estimation

### Gas Costs (Base Network)

| Operation | Estimated Gas | Cost @ 0.1 Gwei |
|-----------|---------------|-----------------|
| Buy (ETH→Token) | ~150,000 | ~$0.0005 |
| Approve | ~50,000 | ~$0.0002 |
| Sell (Token→ETH) | ~200,000 | ~$0.0007 |
| **Per Cycle** (10 buys + 1 sell) | ~1.8M | ~$0.006 |

### Example Costs

For a typical run with:
- Buy amount: 0.002 ETH (~$6)
- Buy interval: 5 minutes
- Sell after: 10 buys
- Running 24 hours:

**Daily Volume**: ~12 cycles × 10 buys × $6 = **$720 volume**  
**Daily Gas Cost**: ~12 cycles × $0.006 = **~$0.07**

## 🔐 Auto-Generated Wallet Security

The bot now uses **auto-generated wallets** for enhanced security:

### Benefits

| Feature | Old Method | New Auto-Generated |
|---------|-----------|-------------------|
| Private Key Exposure | User sees and enters key | Key never displayed |
| Copy/Paste Risk | High (clipboard exposure) | None |
| Key Generation | External wallet | Cryptographically secure local generation |
| User Error Risk | Wrong key, format errors | Eliminated |

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  Setup Process                                              │
├─────────────────────────────────────────────────────────────┤
│  1. Bot generates new wallet using eth_account             │
│     └── Uses OS-level entropy (secrets.token_hex)          │
│                                                            │
│  2. Private key encrypted immediately                       │
│     └── PBKDF2-HMAC-SHA256 (480k iterations)               │
│     └── Fernet symmetric encryption                         │
│     └── Random salt per wallet                              │
│                                                            │
│  3. Only public address shown to user                       │
│     └── User funds this address with ETH                   │
│                                                            │
│  4. Encrypted key saved to .wallet.enc (permissions 600)   │
└─────────────────────────────────────────────────────────────┘
```

### Recovery

⚠️ **Important**: Since the private key is never shown, you **must**:
1. Save your wallet address to send funds to it
2. Remember your encryption password (no recovery possible)
3. Consider exporting the wallet later if needed (see below)

### Exporting Your Private Key (Optional)

If you need to access the private key later (e.g., to import into MetaMask):

```bash
# Create a temporary export script
cat > export_wallet.py << 'EOF'
import json
import base64
from cryptography.fernet import Fernet
import hashlib
import getpass

password = getpass.getpass("Enter wallet password: ")

with open(".wallet.enc", "r") as f:
    data = json.load(f)

key = hashlib.sha256(password.encode()).digest()
key = base64.urlsafe_b64encode(key)
f = Fernet(key)
decrypted = f.decrypt(data["encrypted"].encode())

print(f"\nPrivate Key: {decrypted.decode()}")
print("⚠️  Store this securely and delete this script!")
EOF

python export_wallet.py
rm export_wallet.py
```

## 🔒 Security Checklist

Before running with real funds:

- [ ] Wallet has been generated and funded with ETH
- [ ] Wallet address saved for future reference
- [ ] Encryption password is strong (8+ chars) and backed up
- [ ] Wallet file (.wallet.enc) has 600 permissions
- [ ] Dry run tested successfully
- [ ] Machine is secure (no malware, firewall enabled)
- [ ] Bot running in screen/tmux or as service
- [ ] Logs are being written and monitored

## 🐛 Troubleshooting

### "Failed to connect to RPC"

- Bot automatically tries multiple RPC endpoints
- Check internet connection
- Wait a moment and retry

### "Gas price exceeds maximum"

- Network may be congested
- Increase `max_gas_gwei` in config
- Bot will wait for gas prices to drop

### "Insufficient funds"

- Ensure wallet has enough ETH for gas
- Check you're on Base network (chainId 8453)
- Verify buy amount is less than balance

### "Failed to decrypt wallet"

- Wrong password - try again
- Wallet file may be corrupted
- Re-run `python bot.py setup` to generate a new wallet (old wallet will be lost!)

### View Logs

```bash
# Tail log file
tail -f volume_bot.log

# View last 100 lines
tail -n 100 volume_bot.log

# Search for errors
grep ERROR volume_bot.log
```

## 🚀 Deployment

### Running as a Service (systemd)

Create `/etc/systemd/system/compute-bot.service`:

```ini
[Unit]
Description=$COMPUTE Volume Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/path/to/volume_bot
Environment="PYTHONUNBUFFERED=1"
ExecStart=/path/to/venv/bin/python bot.py run
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

### Running with Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY swarm/ ./swarm/

# Don't copy config/wallet - mount as volumes
VOLUME ["/app/config"]

# Set working config path
ENV CONFIG_PATH=/app/config

CMD ["python", "bot.py", "run"]
```

Build and run:

```bash
docker build -t compute-bot .
docker run -v /path/to/config:/app/config compute-bot
```

**Note:** Place `bot_config.json` and `.bot_wallet.enc` in `/path/to/config/`

### Running with PM2

```bash
# Install PM2
npm install -g pm2

# Start bot
pm2 start "python bot.py run" --name compute-bot

# View logs
pm2 logs compute-bot

# Monitor
pm2 monit
```

### Running with screen/tmux

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

## 🧪 Testing

### Dry Run Mode

```bash
# Test without spending real funds
python bot.py run --dry-run
```

In dry run mode:
- No transactions are sent
- All logic is executed
- Perfect for testing configuration

### Check Balances

```bash
python bot.py balance
```

Shows ETH and COMPUTE balances before running.

## ⚠️ Risk Disclaimer

**WARNING**: This is experimental software. Use at your own risk.

- Trading cryptocurrencies involves significant risk
- Smart contract interactions can result in loss of funds
- Gas prices are unpredictable
- Slippage can result in receiving less than expected
- Bot bugs could cause unexpected behavior

**Always test with small amounts first.**

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Commit with clear messages
5. Push to the branch
6. Open a Pull Request

## 📞 Support

For issues and questions:
- Open a GitHub issue
- Check existing issues first
- Include logs (remove sensitive data like addresses/keys)

## 🔗 Links

- **Repository**: https://github.com/kabbalahmonster/base-volume-bot
- **$COMPUTE Token**: `0x696381f39F17cAD67032f5f52A4924ce84e51BA3`
- **Base Explorer**: https://basescan.org

## 🙏 Acknowledgments

- [Web3.py](https://web3py.readthedocs.io/) - Ethereum interaction
- [Rich](https://rich.readthedocs.io/) - Terminal UI
- [Uniswap V3](https://uniswap.org/) - DEX protocol
- [Base](https://base.org/) - L2 blockchain

---

**Happy Trading! 🚀**

*Built by Clawdelia for the Cult of the Shell* 🦑

*Remember: Never invest more than you can afford to lose.*
