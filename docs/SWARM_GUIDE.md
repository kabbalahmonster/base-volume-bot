# Swarm Wallet Feature Guide

## Overview

The Swarm Wallet feature allows you to create and manage multiple wallets for distributed trading volume. Instead of trading from a single wallet, you can create a "swarm" of wallets that cycle through buys and sells, creating more organic-looking volume.

## Security First

⚠️ **IMPORTANT SECURITY NOTES:**

1. **All swarm wallet keys are encrypted** with your password using PBKDF2 + Fernet
2. **Never share your swarm password** - it decrypts all swarm wallet keys
3. **Always reclaim funds before dissolving** - the system prevents dissolving wallets with balance
4. **Keep your main wallet secure** - it's the source of all funds

## Installation

```bash
# Clone the repo
git clone https://github.com/kabbalahmonster/base-volume-bot.git
cd base-volume-bot

# Install dependencies
pip install -r requirements.txt

# Checkout swarm feature
git checkout feature/swarm-wallets
```

## Quick Start

### 1. Setup Your Bot

```bash
python bot.py setup
```

This will:
- Encrypt your main wallet private key
- Create a configuration file

### 2. Create a Swarm

```bash
python bot.py swarm create --count 10
```

Creates 10 new swarm wallets. Each wallet:
- Has its own unique address
- Is encrypted with your password
- Is tracked in `.swarm.json`

### 3. Fund the Swarm

```bash
python bot.py swarm fund --amount-eth 0.01
```

Distributes 0.01 ETH to each swarm wallet from your main wallet.

### 4. Run with Swarm

```bash
python bot.py run --swarm-mode
```

The bot will cycle through swarm wallets for trades.

### 5. Reclaim Funds

When you're done:

```bash
python bot.py swarm reclaim
```

Returns all funds from swarm wallets back to your main wallet.

### 6. Dissolve Swarm

After reclaiming:

```bash
python bot.py swarm dissolve
```

Removes all swarm wallet data (only works if all wallets have zero balance).

## Commands Reference

### `swarm create`

Create new swarm wallets.

```bash
python bot.py swarm create --count 10
```

Options:
- `--count`: Number of wallets to create (default: 5)

### `swarm fund`

Distribute ETH to all swarm wallets.

```bash
python bot.py swarm fund --amount-eth 0.01
```

Options:
- `--amount-eth`: Amount of ETH per wallet (default: 0.002)

**⚠️ Warning:** This sends real ETH from your main wallet!

### `swarm status`

Show swarm wallet status.

```bash
python bot.py swarm status
```

Shows:
- Wallet addresses
- ETH balances
- Number of trades per wallet
- Last used timestamp

### `swarm reclaim`

Return all funds to main wallet.

```bash
python bot.py swarm reclaim --to 0x...  # Optional: different destination
```

Options:
- `--to`: Optional different destination address (default: main wallet)

**⚠️ Confirmation Required:** You must type "RECLAIM" to proceed.

### `swarm dissolve`

Destroy swarm wallets.

```bash
python bot.py swarm dissolve
```

**⚠️ Safety Check:** Only works if ALL wallets have zero balance. Use `reclaim` first!

### `run --swarm-mode`

Run the bot with swarm trading.

```bash
python bot.py run --swarm-mode
```

In swarm mode:
- Bot cycles through wallets round-robin
- Each wallet makes one trade, then moves to next
- Creates distributed, organic-looking volume

### `swarm withdraw`

Withdraw from main wallet or swarm wallets.

```bash
# Withdraw from main wallet
python bot.py withdraw 0xYOUR_ADDRESS --amount 0.5

# Withdraw all ETH from main wallet (keeps gas)
python bot.py withdraw 0xYOUR_ADDRESS

# Withdraw all funds including COMPUTE
python bot.py withdraw 0xYOUR_ADDRESS --compute
```

Options:
- `--amount`: Specific ETH amount (omit for all)
- `--compute`: Also withdraw all COMPUTE tokens

## Configuration

Edit `bot_config.json` for swarm settings:

```json
{
  "chain": "base",
  "buy_amount_eth": 0.002,
  "buy_interval_minutes": 5,
  "sell_after_buys": 10,
  "slippage_percent": 2.0,
  "max_gas_gwei": 0.5,
  "swarm_enabled": true,
  "swarm_size": 10
}
```

## How It Works

### Swarm Creation

1. Generates N random Ethereum wallets
2. Encrypts each private key with your password
3. Stores encrypted keys in `.swarm.json`
4. Displays wallet addresses (not private keys)

### Trading Cycle

1. Bot selects next wallet in round-robin
2. Decrypts wallet key temporarily in memory
3. Executes trade
4. Clears key from memory
5. Moves to next wallet

### Fund Management

- **Distribution:** Main wallet → All swarm wallets
- **Reclamation:** All swarm wallets → Main wallet (or specified address)
- **Safety:** Cannot dissolve wallets with balance

## Best Practices

### Creating a Swarm

1. **Start small:** Create 5-10 wallets for testing
2. **Fund modestly:** 0.01 ETH per wallet is plenty for testing
3. **Test first:** Use `--dry-run` mode
4. **Monitor:** Check `swarm status` regularly

### Running with Swarm

1. **Don't over-trade:** Start with longer intervals (10+ minutes)
2. **Monitor gas:** Keep `max_gas_gwei` reasonable
3. **Watch balances:** Ensure wallets have enough for gas
4. **Log activity:** Review `volume_bot.log` regularly

### Exiting Safely

1. **Stop bot:** Ctrl+C to stop gracefully
2. **Check status:** `python bot.py swarm status`
3. **Reclaim funds:** `python bot.py swarm reclaim`
4. **Verify zero balances:** Check status again
5. **Dissolve swarm:** `python bot.py swarm dissolve`

## Security FAQ

**Q: Where are swarm wallet keys stored?**
A: Encrypted in `.swarm.json` using PBKDF2 + Fernet. Requires your password to decrypt.

**Q: Can someone steal funds if they get .swarm.json?**
A: No, they need your password to decrypt the keys.

**Q: What happens if I forget my password?**
A: You cannot recover swarm wallets. Always reclaim funds before potential password loss.

**Q: Is it safe to commit .swarm.json to git?**
A: No! Add `.swarm.json` to .gitignore. It contains encrypted keys.

**Q: Can I use the same password as my main wallet?**
A: Technically yes, but for security use different passwords.

**Q: What if a transaction fails?**
A: The bot logs errors and continues to next wallet. Check logs for details.

## Troubleshooting

### "No wallets in swarm"

Run `python bot.py swarm create --count 5` first.

### "Insufficient balance for distribution"

Your main wallet needs more ETH. Check with `python bot.py balance`.

### "Cannot dissolve - wallets with non-zero balance"

Run `python bot.py swarm reclaim` first to return all funds.

### "Failed to decrypt wallet"

Wrong password. Try again with correct password.

### "Gas too high"

Increase `max_gas_gwei` in config or wait for lower gas.

## Advanced Usage

### Custom Swarm Size

```bash
# Create 50 wallets for massive volume
python bot.py swarm create --count 50

# Fund with 0.005 ETH each (250x smaller trades)
python bot.py swarm fund --amount-eth 0.005
```

### Multi-Swarm Strategy

You can maintain multiple swarms by renaming `.swarm.json`:

```bash
# Save current swarm
mv .swarm.json .swarm-backup-1.json

# Create new swarm
python bot.py swarm create --count 10

# Switch back
mv .swarm.json .swarm-backup-2.json
mv .swarm-backup-1.json .swarm.json
```

### Programmatic Access

```python
from swarm import SwarmManager

manager = SwarmManager(main_key, password, w3)

# Create swarm
addresses = manager.create_swarm(10)

# Fund
manager.distribute_funds(0.01)

# Get next wallet
account, wallet_info = manager.get_next_wallet()

# Reclaim
manager.reclaim_all_funds()
```

## Support

For issues or questions:
1. Check logs: `volume_bot.log`
2. Review this guide
3. Check GitHub issues

## License

MIT License - See LICENSE file

---

*Built by Clawdelia for the Cult of the Shell* 🦑
