# 🤖 $COMPUTE Volume Bot

A production-ready, secure Python trading bot for generating volume on $COMPUTE token on Base blockchain.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Base Chain](https://img.shields.io/badge/Base-Chain-0052FF)](https://base.org)

## 📋 Features

- **🔐 Secure**: Private key encryption with PBKDF2 + Fernet
- **⛽ Gas Optimized**: EIP-1559 support, dynamic gas pricing
- **🔄 Retry Logic**: Exponential backoff for failed transactions
- **📊 Rich CLI**: Beautiful terminal UI with progress bars and tables
- **🧪 Dry Run Mode**: Test without spending real funds
- **📈 Health Monitoring**: Built-in health checks and status reporting
- **🛡️ Slippage Protection**: Configurable slippage tolerance
- **📝 Comprehensive Logging**: File and console logging

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- An Ethereum wallet with ETH on Base
- Base RPC endpoint (public or private)

### Installation

```bash
# Clone or download the bot
git clone <repository-url>
cd volume_bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Initialize configuration (interactive setup)
python bot.py init

# Or specify custom config path
python bot.py init --config ./my_config.yaml
```

You'll be prompted for:
- Private key (encrypted, never stored in plain text)
- RPC URL
- Buy amount and interval
- Gas settings
- Encryption password

### Run the Bot

```bash
# Start trading
python bot.py run

# With options
python bot.py run --verbose --config ./custom_config.yaml

# Dry run mode (no real transactions)
python bot.py run --dry-run
```

## 📖 Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize configuration with encrypted keys |
| `run` | Start the trading bot |
| `status` | Check configuration status |
| `wallet-info` | Display wallet balances |

## ⚙️ Configuration

### Default Settings

```yaml
# Network
rpc_url: https://mainnet.base.org
chain_id: 8453

# Token Addresses
compute_token: "0x696381f39F17cAD67032f5f52A4924ce84e51BA3"
weth_address: "0x4200000000000000000000000000000000000006"

# Trading Parameters
buy_amount_eth: 0.002          # Amount per buy (~$5-10)
buy_interval_seconds: 300      # 5 minutes between buys
sell_after_buys: 10            # Sell after 10 buys

# Gas Settings
max_gas_price_gwei: 5.0        # Maximum gas price
slippage_percent: 2.0          # 2% slippage tolerance
gas_limit_buffer: 1.2          # 20% gas buffer

# Operation
max_retries: 3
retry_delay_seconds: 5
dry_run: false
log_level: INFO
```

### Security Notes

- **Private keys are encrypted** using your password + random salt
- **Config file permissions** are set to 600 (owner read/write only)
- **Never commit** your config file to version control
- **Backup your encryption password** - without it, the private key cannot be recovered

## 🏗️ Architecture

```
volume_bot/
├── bot.py           # CLI entry point and main loop
├── config.py        # Configuration management with encryption
├── trader.py        # Uniswap V3 trading logic
├── wallet.py        # Secure wallet operations
├── utils.py         # Helpers, gas optimization, logging
├── requirements.txt # Python dependencies
└── README.md        # This file
```

### Trading Flow

1. **Initialize**: Load encrypted config, connect to Base
2. **Buy Loop**: Execute buys at configured intervals
3. **Count**: Track number of successful buys
4. **Sell Trigger**: When buy count reaches threshold, sell all
5. **Repeat**: Reset counter and continue

### Security Flow

```
User Password + Salt → PBKDF2 → Fernet Key → Encrypt Private Key
                                              ↓
                                    Config File (encrypted)
                                              ↓
User Password + Salt → PBKDF2 → Fernet Key → Decrypt at Runtime
```

## 💰 Cost Estimation

### Gas Costs (Base Network)

| Operation | Estimated Gas | Cost @ 1 Gwei |
|-----------|---------------|---------------|
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

## 🔒 Security Checklist

Before running with real funds:

- [ ] Private key stored in encrypted config only
- [ ] Encryption password is strong and backed up
- [ ] Config file has 600 permissions
- [ ] Wallet has sufficient ETH for gas
- [ ] Dry run tested successfully
- [ ] RPC endpoint is trusted
- [ ] Machine is secure (no malware, firewall enabled)
- [ ] Bot running in screen/tmux or as service
- [ ] Logs are being written and monitored

## 🐛 Troubleshooting

### "Failed to connect to RPC"

- Verify RPC URL is correct and accessible
- Check firewall settings
- Try a different RPC endpoint

### "Gas price exceeds maximum"

- Network may be congested
- Increase `max_gas_price_gwei` in config
- Bot will wait for gas prices to drop

### "Insufficient funds"

- Ensure wallet has enough ETH for gas
- Check you're on Base network (chainId 8453)
- Verify buy amount is less than balance

### "Transaction failed"

- Check transaction on [BaseScan](https://basescan.org)
- Verify token contract address
- Check slippage settings
- Review logs for detailed error

## 📊 Monitoring

### View Logs

```bash
# Tail log file
tail -f bot.log

# View last 100 lines
tail -n 100 bot.log

# Search for errors
grep ERROR bot.log
```

### Health Checks

The bot performs automatic health checks:
- RPC connection status
- Node sync status
- Gas price monitoring
- Wallet balance checks

### Metrics

The bot tracks:
- Total trades executed
- Successful/failed trade ratio
- Total gas spent
- Current buy count
- ETH and COMPUTE balances

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

### Testnet (if available)

You can test on Base Sepolia before mainnet:

1. Get testnet ETH from [Base Sepolia Faucet](https://www.coinbase.com/faucets/base-sepolia-faucet)
2. Update RPC URL to Sepolia endpoint
3. Run with small amounts

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
ExecStart=/path/to/venv/bin/python bot.py run --config /path/to/config.yaml
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

# Don't copy config - mount it as volume
VOLUME ["/app/config"]

CMD ["python", "bot.py", "run", "--config", "/app/config/bot_config.yaml"]
```

Build and run:

```bash
docker build -t compute-bot .
docker run -v /path/to/config:/app/config compute-bot
```

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

## 📝 Environment Variables

You can also configure via environment variables (useful for Docker):

```bash
export COMPUTE_BOT_RPC_URL="https://mainnet.base.org"
export COMPUTE_BOT_PASSWORD="your-encryption-password"
export COMPUTE_BOT_LOG_LEVEL="INFO"
```

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
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📞 Support

For issues and questions:
- Open a GitHub issue
- Check existing issues first
- Include logs and configuration (remove sensitive data)

## 🙏 Acknowledgments

- [Web3.py](https://web3py.readthedocs.io/) - Ethereum interaction
- [Rich](https://rich.readthedocs.io/) - Terminal UI
- [Uniswap V3](https://uniswap.org/) - DEX protocol
- [Base](https://base.org/) - L2 blockchain

---

**Happy Trading! 🚀**

*Remember: Never invest more than you can afford to lose.*
