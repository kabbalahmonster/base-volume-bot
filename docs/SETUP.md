# Volume Bot Setup Guide

Complete setup instructions for the COMPUTE Volume Bot.

## Prerequisites

- Python 3.9+
- Git
- ETH on Base network for gas

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/kabbalahmonster/base-volume-bot.git
cd base-volume-bot
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Setup

```bash
python bot.py setup
```

This will:
- Generate a new wallet
- Encrypt and save the private key
- Create default configuration

**IMPORTANT:** Save your wallet address and fund it with ETH on Base.

### 5. Configure API Keys (Optional but Recommended)

Create `.env` file:

```bash
# 0x API Key - Get from https://0x.org
ZEROX_API_KEY=your_key_here

# 1inch API Key - Get from https://portal.1inch.dev
ONEINCH_API_KEY=your_key_here
```

Or edit `bot_config.json` directly.

### 6. Test Configuration

```bash
# Check balances
python bot.py balance

# Test with dry-run
python bot.py run --dry-run

# Run live (with confirmation prompts disabled)
python bot.py run
```

## Trading Specific Tokens

### BNKR (Works with Aerodrome)

```bash
python bot.py run --token-address 0x22aF33FE49fD1Fa80c7149773dDe5890D3c76F3b
```

### COMPUTE (V4-only - requires 0x or direct V4)

**Current Status:** Direct V4 not yet implemented. Use 0x aggregator:

```bash
# Requires 0x API key configured
python bot.py run --token-address 0x696381f39F17cAD67032f5f52A4924ce84e51BA3
```

## Configuration Options

Edit `bot_config.json`:

```json
{
  "buy_amount_eth": 0.002,
  "buy_interval_seconds": 300,
  "sell_after_buys": 10,
  "slippage_percent": 2.0,
  "max_gas_price_gwei": 5.0,
  "zerox_api_key": "optional",
  "oneinch_api_key": "optional"
}
```

## Troubleshooting

### "No wallet file found"
Run `python bot.py setup` first.

### "Insufficient ETH balance"
Fund your wallet with ETH on Base network.

### "No DEX found with liquidity"
Token may not have liquidity on supported DEXs.

### "0x API error 401"
Your API key is invalid or expired.

## Security Best Practices

1. Use strong encryption password (16+ chars)
2. Store API keys in `.env`, not in config
3. Regularly backup `.bot_wallet.enc`
4. Never share your private key
5. Use hardware wallet for large amounts

## Support

- GitHub Issues: https://github.com/kabbalahmonster/base-volume-bot/issues
- Documentation: See README.md
