# Swarm Trading Guide

## Overview

Swarm mode coordinates multiple wallets for volume generation. This distributes trading across several addresses, making volume appear more organic.

## Quick Start

### 1. Create Swarm Wallets

```bash
python swarm_cli.py create --count 3
```

You'll be prompted for:
- **Swarm password** (encrypts all wallet keys, min 8 chars)
- Creates `swarm_wallets.enc` (3 encrypted private keys)

**Output:**
```
✓ Swarm created with 3 wallets
Wallet 0: 0xABC...123
Wallet 1: 0xDEF...456
Wallet 2: 0xGHI...789
Password backup saved to: swarm_password_backup.txt
```

⚠️ **SAVE THE PASSWORD!** Without it, wallets are unrecoverable.

### 2. Fund Swarm Wallets

```bash
python swarm_cli.py fund --amount 0.001
```

You'll be prompted for:
- **Main wallet private key** (for funding, not stored)

This sends 0.001 ETH to each of the 3 wallets.

**Requirements:**
- Main wallet needs: `(3 × 0.001) + 0.005 gas reserve = 0.008 ETH`

### 3. Configure Swarm Trading

Edit `swarm_config.json`:
```json
{
  "rotation_mode": "round_robin",
  "buys_per_cycle": 1,
  "buy_interval_minutes": 2,
  "auto_sell": true,
  "max_cycles": 1
}
```

### 4. Run Swarm Trading

```bash
python swarm_cli.py run
```

**What happens:**
1. Wallet 0 buys → wait 2 min
2. Wallet 1 buys → wait 2 min
3. Wallet 2 buys → wait 2 min
4. All wallets sell
5. Stop (max_cycles: 1 reached)

### 5. Reclaim Funds

```bash
python swarm_cli.py reclaim --main-address 0xYourMainWallet
```

This:
- Sells all tokens for ETH
- Sends all ETH back to your main wallet
- Keeps minimal gas reserve in swarm wallets

### 6. Dissolve Swarm (Optional)

After reclaiming, archive the wallet file:
```bash
mv swarm_wallets.enc swarm_wallets.enc.archived.$(date +%Y%m%d)
```

## Rotation Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `round_robin` | Sequential (0,1,2,0,1,2...) | Balanced usage |
| `random` | Random selection | Maximum distribution |
| `least_used` | Fewest trades first | Even wear |
| `balance_based` | Highest ETH balance first | Optimize gas |

## Safety Limits

Always use these safeguards:

```json
{
  "max_cycles": 5,
  "buy_amount_eth": 0.0005,
  "slippage_percent": 2.0
}
```

**Test first:**
```bash
python swarm_cli.py run --dry-run
```

## Troubleshooting

### "Insufficient funds for gas"
- Increase `funder_gas_reserve` in config
- Or fund main wallet with more ETH

### "No wallets found"
- Check `swarm_wallets.enc` exists
- Verify password is correct

### "Nonce too low" during funding
- Wait 10 seconds and retry
- RPC may be lagging

## Best Practices

1. **Start small**: Test with 2-3 wallets first
2. **Dry run**: Always test with `--dry-run`
3. **Monitor gas**: Keep extra ETH for gas spikes
4. **Backup password**: Without it, funds are lost
5. **Reclaim promptly**: Don't leave funds in swarm wallets

## Example: Full Cycle

```bash
# 1. Setup
python swarm_cli.py create --count 3
# Save password: MySecurePass123

# 2. Fund (main wallet needs ~0.01 ETH)
python swarm_cli.py fund --amount 0.001

# 3. Run (1 buy each, then sell)
python swarm_cli.py run --buys-per-cycle 1 --max-cycles 1

# 4. Reclaim
python swarm_cli.py reclaim --main-address 0xYourWallet

# 5. Verify empty
python swarm_cli.py status

# 6. Archive
mv swarm_wallets.enc swarm_wallets.enc.archived.20260216
```

## Gas Estimates

Per wallet, per cycle:
- Funding: ~21,000 gas
- Buy (0x): ~180,000 gas
- Approval: ~50,000 gas (first sell only)
- Sell (0x): ~180,000 gas
- Reclaim: ~21,000 gas

**Total per wallet:** ~450,000 gas ≈ 0.0002-0.0004 ETH at normal gas prices

## Security Notes

- Swarm passwords are hashed with PBKDF2
- Private keys never leave encrypted file
- Main wallet key only used for funding (not stored)
- Always verify addresses on BaseScan before funding
