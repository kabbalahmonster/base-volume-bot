# ❓ Frequently Asked Questions (FAQ)

Quick answers to common questions about the $COMPUTE Volume Bot.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Wallets & Security](#wallets--security)
- [Trading & Configuration](#trading--configuration)
- [Swarm Mode](#swarm-mode)
- [Troubleshooting](#troubleshooting)
- [Deployment](#deployment)
- [Costs & Fees](#costs--fees)

---

## Getting Started

### What is the Volume Bot?

The Volume Bot is a Python-based automated trading system that generates trading volume for the $COMPUTE token on Base blockchain. It buys small amounts at regular intervals and sells after a set number of purchases.

### Is this free to use?

Yes! The bot is open-source (MIT license) with no subscription fees. You only pay:
- Gas fees for transactions
- Your own trading capital

### What do I need to get started?

**Minimum:**
- Python 3.9+
- 0.01 ETH on Base network
- Basic command line knowledge

**Recommended:**
- Server or VPS for 24/7 operation
- 0.05+ ETH for sustained trading

### How long does setup take?

| Step | Time |
|------|------|
| Install dependencies | 2-5 minutes |
| Setup wallet | 2 minutes |
| Fund wallet | 5-10 minutes |
| Test run | 5 minutes |
| **Total** | **15-25 minutes** |

### Do I need programming experience?

No! The bot is designed for non-technical users:
- Simple commands: `python bot.py run`
- Interactive setup
- Clear error messages
- Comprehensive documentation

---

## Wallets & Security

### How are private keys stored?

Private keys are:
1. **Generated locally** using cryptographically secure randomness
2. **Encrypted immediately** with PBKDF2-HMAC-SHA256 (600k iterations)
3. **Stored in `.wallet.enc`** with 600 permissions (owner only)
4. **Never transmitted** or exposed to the internet

### What if I forget my password?

⚠️ **There is no password recovery.**

Options:
1. **Remember your password** - Store it in a password manager
2. **Export private key** - Before forgetting (see below)
3. **Start fresh** - Re-run setup (loses old wallet)

### How do I export my private key?

```bash
# Create export script
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

### Can I use my existing wallet?

The bot is designed for **auto-generated wallets** for security. However, you can:

1. Export the auto-generated wallet key
2. Import into MetaMask
3. Or fund the auto-generated wallet from your main wallet

### Is this safe to run on a server?

Yes, if you follow security best practices:

- ✅ Use firewall (only allow necessary ports)
- ✅ Regular security updates
- ✅ Run as non-root user
- ✅ Use SSH keys (not passwords)
- ✅ Monitor server access
- ✅ Backup wallet file securely

See [SECURITY.md](SECURITY.md) for full guidelines.

### Can someone steal my funds?

Only if they have:
1. Access to your server AND
2. Your encryption password

Without both, funds are safe. The private key is encrypted at rest.

---

## Trading & Configuration

### How much ETH do I need?

| Strategy | ETH Needed | Duration |
|----------|------------|----------|
| Testing | 0.01 | Few cycles |
| Small Scale | 0.05 | ~20 cycles |
| Standard | 0.1 | ~40 cycles |
| Aggressive | 0.5+ | 200+ cycles |

Each cycle = `buy_amount_eth` × `sell_after_buys`

### How much can I make?

**Important:** This bot generates volume, not profit. You may experience:

- **Trading losses** due to price movement
- **Gas costs** for each transaction
- **Slippage** on each trade

The bot is designed for:
- Increasing token visibility
- Supporting project volume
- Creating trading activity

### What settings should I use?

**Conservative (Recommended for beginners):**
```json
{
  "buy_amount_eth": 0.001,
  "buy_interval_minutes": 15,
  "sell_after_buys": 20,
  "slippage_percent": 1.0
}
```

**Standard:**
```json
{
  "buy_amount_eth": 0.002,
  "buy_interval_minutes": 5,
  "sell_after_buys": 10,
  "slippage_percent": 2.0
}
```

### Can I change settings while running?

Yes!
1. Edit `bot_config.json`
2. Stop bot: `Ctrl+C`
3. Start bot: `python bot.py run`
4. New settings take effect immediately

### What happens if I stop the bot?

- Pending transactions complete
- Current position remains
- Resume anytime with `python bot.py run`
- No penalties for stopping

### Can I run multiple bots?

Yes! Options:
1. **Different wallets** - Each bot has separate wallet
2. **Swarm mode** - Coordinated multi-wallet trading
3. **Different tokens** - Modify token address in config

---

## Swarm Mode

### What is swarm mode?

Swarm mode runs multiple trading wallets simultaneously:
- **Queen wallet** - Main funding source
- **Worker wallets** - Execute trades
- **Coordinated** - Synchronized operation

### Why use swarm mode?

| Benefit | Description |
|---------|-------------|
| **Volume Multiplication** | 10 wallets = 10x volume |
| **Risk Distribution** | Loss limited per wallet |
| **Organic Appearance** | Multiple addresses trading |
| **Efficiency** | Fund/reclaim all at once |

### How many wallets should I create?

| Count | Use Case | Funding Needed |
|-------|----------|----------------|
| 3-5 | Testing | 0.03-0.05 ETH |
| 10-20 | Small operation | 0.1-0.2 ETH |
| 50+ | Large operation | 0.5+ ETH |

### How do I fund swarm wallets?

```bash
# Fund all wallets from main wallet
python swarm_cli.py fund --main-key <PRIVATE_KEY> --amount 0.02
```

### Can I lose money in swarm mode?

Yes. Each worker wallet:
- Trades independently
- Can have losses
- Has gas costs

**Risk mitigation:**
- Start small
- Monitor regularly
- Reclaim funds frequently

---

## Troubleshooting

### "Failed to decrypt wallet"

**Cause:** Wrong password

**Solutions:**
1. Try password again (case-sensitive)
2. Check for extra spaces
3. If forgotten, must re-run setup

### "Insufficient funds"

**Cause:** Not enough ETH for trade + gas

**Solutions:**
1. Check balance: `python bot.py balance`
2. Send more ETH to wallet
3. Reduce `buy_amount_eth` in config

### "Gas price exceeds maximum"

**Cause:** Network congestion

**Solutions:**
1. Increase `max_gas_gwei` in config
2. Wait for less congested period
3. Use "aggressive" gas strategy

### "Failed to connect to RPC"

**Cause:** Network issue or RPC down

**Solutions:**
1. Check internet connection
2. Bot auto-retries other RPCs
3. Wait and retry

### "Transaction failed"

**Common causes:**
- Slippage too low → Increase `slippage_percent`
- Gas limit too low → Increase `gas_limit_buffer`
- Token approval needed → Bot handles automatically
- Network congestion → Retry later

### "No quotes available"

**Cause:** Router can't find trading path

**Solutions:**
1. Try different router: `--router uniswap_v3`
2. Increase slippage tolerance
3. Check token contract address

### Bot stops unexpectedly

**Check:**
1. View logs: `tail -f volume_bot.log`
2. Check disk space: `df -h`
3. Check memory: `free -m`
4. Review error messages

### Where are the logs?

```bash
# Default log location
./volume_bot.log

# Follow logs in real-time
tail -f volume_bot.log

# Search for errors
grep ERROR volume_bot.log

# View last 100 lines
tail -n 100 volume_bot.log
```

---

## Deployment

### Should I run on a server?

**Local machine:**
- ✅ Free
- ✅ Easy setup
- ❌ Must keep computer on
- ❌ Internet dependent

**VPS/Server:**
- ✅ 24/7 operation
- ✅ Stable internet
- ✅ Professional monitoring
- ❌ Monthly cost (~$5-20)

### Recommended VPS providers?

| Provider | Price | Location | Notes |
|----------|-------|----------|-------|
| DigitalOcean | $6/mo | Global | Simple, reliable |
| AWS Lightsail | $5/mo | Global | AWS ecosystem |
| Hetzner | €4/mo | Europe | Great value |
| Vultr | $5/mo | Global | Good performance |

### How do I monitor the bot remotely?

**Options:**

1. **SSH + tail logs**
   ```bash
   ssh server "tail -f /opt/volume_bot/volume_bot.log"
   ```

2. **Systemd status**
   ```bash
   ssh server "sudo systemctl status compute-bot"
   ```

3. **Log forwarding** (to service like Datadog, Papertrail)

4. **Telegram notifications** (custom script)

### Can I run on Raspberry Pi?

Yes! Requirements:
- Raspberry Pi 4 (2GB+ RAM)
- Raspberry Pi OS 64-bit
- Good cooling (trading is CPU intensive)

---

## Costs & Fees

### What are the total costs?

**Fixed Costs:**
- Server (optional): $0-20/month

**Variable Costs (per trade):**
- Gas fees: ~$0.0005-0.001 per transaction
- Trading slippage: 0.5-3% typically

**Example Daily Cost (Standard settings):**
- 144 buys/day × $0.0005 = $0.07 gas
- 14 sells/day × $0.0007 = $0.01 gas
- **Total: ~$0.08/day**

### How much gas should I expect?

| Operation | Gas Used | Cost @ 0.1 Gwei |
|-----------|----------|-----------------|
| Buy | 150,000 | $0.0005 |
| Approve | 50,000 | $0.0002 |
| Sell | 200,000 | $0.0007 |

Base network gas is typically 0.1-0.5 Gwei.

### Can I reduce gas costs?

**Yes:**
1. Use Uniswap V4 router (lowest gas) - Requires `uniswap-universal-router-decoder` library
2. Increase `buy_interval_minutes`
3. Trade during low-congestion periods
4. Set `gas_price_strategy` to "conservative"

---

## V4 & COMPUTE Trading

### What is V4 trading?

Uniswap V4 is the latest version with:
- **Singleton architecture** - All pools in one contract
- **Flash accounting** - Internal balance tracking
- **Hooks** - Customizable pool behavior
- **Lower gas** - More efficient than V3

### How do I trade COMPUTE (V4-only token)?

**Install V4 support:**
```bash
pip install uniswap-universal-router-decoder
```

**Then run:**
```bash
python bot.py run --token-address 0x696381f39F17cAD67032f5f52A4924ce84e51BA3
```

The bot will automatically:
1. Detect V4 pools
2. Use the encoder library
3. Execute proper V4 swaps

### Which tokens work with V4?

**V4-Only Tokens:**
- $COMPUTE - Requires V4 router

**V2/V3 Tokens:**
- $BNKR - Works with Aerodrome (recommended)
- Most other tokens - Use multi-DEX router

### V4 vs V3 gas costs?

| Router | Gas per Swap | Best For |
|--------|-------------|----------|
| V4 | ~50,000 | COMPUTE only |
| V3 | ~150,000 | Deep liquidity tokens |
| V2/Aerodrome | ~120,000 | BNKR and most tokens |

### What if V4 swap fails?

**Check:**
1. Library installed: `pip show uniswap-universal-router-decoder`
2. On correct branch: `feature/v4-universal-router`
3. Have enough ETH for gas
4. Token has V4 liquidity

**If still failing:**
- Use Aerodrome for BNKR instead
- Wait for 0x aggregator V4 support
- Check GitHub issues for updates

### Is there a fee to the developers?

No! The bot is completely free and open-source. No:
- Developer fees
- Subscription costs
- Hidden charges

Only blockchain gas fees apply.

---

## Still Have Questions?

- 📖 [Setup Guide](SETUP.md) - Detailed installation
- ⚙️ [Configuration](CONFIGURATION.md) - All settings explained
- 🌐 [Router Guide](ROUTERS.md) - DEX router details
- 🔒 [Security Guide](SECURITY.md) - Security best practices
- 🐛 [GitHub Issues](https://github.com/kabbalahmonster/base-volume-bot/issues) - Bug reports

---

**Happy Trading! 🚀**
