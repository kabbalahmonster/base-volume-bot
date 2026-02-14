# 🎓 Swarm Mode Tutorial

A hands-on, step-by-step guide to creating and running your first wallet swarm.

**Estimated time:** 45 minutes  
**Difficulty:** Beginner  
**Prerequisites:** Basic familiarity with command line

---

## What You'll Learn

By the end of this tutorial, you'll be able to:

1. ✅ Create a wallet swarm configuration
2. ✅ Fund multiple worker wallets
3. ✅ Start and monitor a running swarm
4. ✅ Reclaim funds back to your main wallet
5. ✅ Troubleshoot common issues

---

## Tutorial Overview

```
Step 1: Setup (5 min)
    ↓
Step 2: Create Your First Swarm (10 min)
    ↓
Step 3: Fund Your Workers (5 min)
    ↓
Step 4: Start Trading (10 min)
    ↓
Step 5: Monitor Progress (10 min)
    ↓
Step 6: Reclaim Funds (5 min)
```

---

## Step 1: Setup

### 1.1 Verify Installation

First, make sure the volume bot is installed:

```bash
cd volume_bot

# Verify Python version
python --version  # Should be 3.9 or higher

# Check dependencies
pip list | grep -E "(web3|rich|cryptography)"
```

Expected output:
```
web3              6.x.x
rich              13.x.x
cryptography      41.x.x
```

If not installed:
```bash
pip install -r requirements.txt
```

### 1.2 Check Swarm Command

```bash
python swarm.py --help
```

You should see the swarm command help output.

### 1.3 Prepare Your Queen Wallet

Your **queen wallet** is your main funding source. It should:

- Be separate from your primary wallet
- Have at least **0.05 ETH** for this tutorial
- Be configured in `bot_config.yaml`

```bash
# Verify queen wallet is set up
python bot.py balance
```

Expected output:
```
💰 Wallet Balances
Address: 0xYourQueenAddress...

  ETH: 0.5
  $COMPUTE: 0.0
```

> ⚠️ **Warning:** Never use your main wallet as the queen. Create a dedicated wallet for swarm operations.

---

## Step 2: Create Your First Swarm

### 2.1 Initialize Swarm Configuration

Run the interactive setup:

```bash
python swarm.py init
```

**Follow the prompts:**

```
🐝 Swarm Initialization

Enter swarm name: tutorial_swarm
Number of workers (2-50): 3
Funding per worker (ETH): 0.005
Queen wallet password: ********

Choose strategy:
  [1] uniform      - All workers trade identically
  [2] staggered    - Workers start at different times  ← SELECT THIS
  [3] randomized   - Random intervals and amounts
  [4] custom       - Advanced configuration

Select: 2

✓ Swarm 'tutorial_swarm' created!
✓ 3 worker wallets generated
✓ Configuration saved to swarm_configs/tutorial_swarm.yaml
```

### 2.2 Examine the Configuration

Let's look at what was created:

```bash
# View the config file
cat swarm_configs/tutorial_swarm.yaml
```

**Key sections to understand:**

```yaml
# The swarm identity
swarm_name: tutorial_swarm

# Your queen wallet reference
queen_wallet:
  config_path: ./bot_config.yaml

# 3 workers will be created
workers:
  count: 3
  name_prefix: worker

# Each gets 0.005 ETH + gas reserve
funding:
  amount_per_worker_eth: 0.005
  gas_reserve_per_worker_eth: 0.002

# Staggered strategy settings
strategy:
  type: staggered
  config:
    base_interval_minutes: 5
    stagger_offset_seconds: 30
```

### 2.3 List Generated Files

```bash
# See what was created
ls -la swarm_configs/
ls -la swarm_configs/tutorial_swarm/
ls -la swarm_configs/tutorial_swarm/workers/
```

Expected structure:
```
swarm_configs/
├── tutorial_swarm.yaml          # Main config
└── tutorial_swarm/
    ├── workers/
    │   ├── worker_01.enc        # Encrypted key
    │   ├── worker_02.enc
    │   └── worker_03.enc
    └── logs/
```

> ℹ️ **Note:** Worker private keys are encrypted and can only be decrypted with your queen wallet password.

---

## Step 3: Fund Your Workers

### 3.1 Check Funding Requirements

```bash
python swarm.py fund tutorial_swarm --dry-run
```

Expected output:
```
🐝 Funding Swarm: tutorial_swarm

Required: 0.021 ETH
  - Workers: 3 × 0.007 ETH = 0.021 ETH
  - Gas estimate: ~0.0003 ETH
  
Queen Balance: 0.5 ETH ✓

Dry run complete. No transactions sent.
Run without --dry-run to execute.
```

### 3.2 Execute Funding

```bash
python swarm.py fund tutorial_swarm
```

**You'll see:**

```
🐝 Funding Swarm: tutorial_swarm

Queen Balance: 0.5 ETH ✓
Required: 0.021 ETH

Funding workers:
  [1/3] worker_01: 0x7a3F...9E2D ← 0.007 ETH
        Transaction: 0xabc123...
        Waiting for confirmation...
        ✓ Confirmed (block: 12345678)
        
  [2/3] worker_02: 0x9B4C...1A5F ← 0.007 ETH
        Transaction: 0xdef456...
        ✓ Confirmed (block: 12345679)
        
  [3/3] worker_03: 0x2D8E...7C4B ← 0.007 ETH
        Transaction: 0xghi789...
        ✓ Confirmed (block: 12345680)

✓ All workers funded successfully!
Gas spent: 0.000315 ETH
Remaining queen balance: 0.478685 ETH
```

### 3.3 Verify Balances

```bash
python swarm.py balance tutorial_swarm
```

Expected output:
```
🐝 Swarm Balances: tutorial_swarm

Worker     Address           ETH Balance    Status
───────────────────────────────────────────────
worker_01  0x7a3F...9E2D     0.0070        ✓
worker_02  0x9B4C...1A5F     0.0070        ✓
worker_03  0x2D8E...7C4B     0.0070        ✓

Total: 0.021 ETH
Queen: 0.478 ETH
```

> ✅ **Checkpoint:** Your workers are now funded and ready to trade!

---

## Step 4: Start Trading

### 4.1 Start the Swarm

```bash
python swarm.py start tutorial_swarm
```

**Output:**
```
🐝 Starting Swarm: tutorial_swarm

Configuration:
  Workers: 3
  Strategy: staggered
  Start delay: 30s between workers
  Mode: LIVE (real transactions)

⚠️  WARNING: This will execute real trades with real funds!
   Press Ctrl+C within 5 seconds to cancel...

Starting workers:
  ✓ worker_01 started (0x7a3F...9E2D)
    Trading config: 0.002 ETH per buy, 5 min interval
    
  ⏳ Waiting 30s before starting worker_02...
  
  ✓ worker_02 started (0x9B4C...1A5F)
    Trading config: 0.002 ETH per buy, 5 min interval
    
  ⏳ Waiting 30s before starting worker_03...
  
  ✓ worker_03 started (0x2D8E...7C4B)
    Trading config: 0.002 ETH per buy, 5 min interval

✓ All 3 workers started successfully!

═══════════════════════════════════════════════════
  Swarm is now RUNNING
  Press Ctrl+C to stop all workers
═══════════════════════════════════════════════════

[worker_01] 🛒 Buy Attempt 1/10
[worker_01] Swapping 0.002 ETH for $COMPUTE...
[worker_01] Transaction: 0xjkl012...
[worker_01] ✓ Buy successful!
```

### 4.2 Understanding the Output

Each worker will log its activity:

| Message | Meaning |
|---------|---------|
| `🛒 Buy Attempt X/Y` | Worker is executing a buy |
| `⏳ Waiting...` | Countdown to next trade |
| `✓ Buy successful!` | Trade executed successfully |
| `💰 SELLING ALL` | Sell cycle triggered |
| `Cycle complete!` | Worker reset and starting new cycle |

### 4.3 Let It Run

**Keep the swarm running for at least 15-20 minutes** to see multiple trades.

While waiting, you can:
- Open a new terminal to check status (Step 5)
- Read about what's happening behind the scenes
- Grab a coffee ☕

### What's Happening Behind the Scenes?

```
Timeline (staggered strategy):

T+0s    worker_01 starts trading
T+30s   worker_02 starts trading  
T+60s   worker_03 starts trading

Each worker:
├── Buys 0.002 ETH worth of $COMPUTE every 5 minutes
├── Tracks buy count
├── After 10 buys → sells entire position
├── Resets counter
└── Repeats cycle
```

---

## Step 5: Monitor Progress

### 5.1 Check Status (New Terminal)

Open a new terminal window/tab:

```bash
cd volume_bot
python swarm.py status tutorial_swarm
```

**Expected output:**
```
┌────────────────────────────────────────────────────────────────┐
│                    🐝 Swarm Status                              │
│                  tutorial_swarm                                │
├────────────────────────────────────────────────────────────────┤
│ Active: 3/3 workers   Uptime: 12m 30s                          │
├────────────────────────────────────────────────────────────────┤
│ Worker     Address           Status    Buys    Balance  $COMP  │
│ ────────────────────────────────────────────────────────────── │
│ worker_01  0x7a3F...9E2D  ● ACTIVE    3/10    0.003    12.5   │
│ worker_02  0x9B4C...1A5F  ● ACTIVE    2/10    0.005     8.3   │
│ worker_03  0x2D8E...7C4B  ● ACTIVE    1/10    0.006     4.1   │
├────────────────────────────────────────────────────────────────┤
│ Total Volume: ~$36   Trades: 6   Gas Spent: 0.0008 ETH         │
└────────────────────────────────────────────────────────────────┘
```

### 5.2 Watch Mode

For live updates:

```bash
python swarm.py status tutorial_swarm --watch 5
```

This refreshes every 5 seconds. Press `Ctrl+C` to exit.

### 5.3 Check Individual Worker

```bash
# View logs for worker_01
python swarm.py logs tutorial_swarm worker_01

# Follow live logs
python swarm.py logs tutorial_swarm worker_01 --follow
```

### 5.4 View Statistics

```bash
python swarm.py stats tutorial_swarm
```

**Output:**
```
🐝 Swarm Statistics: tutorial_swarm

Period: Last 24 hours

Trading:
  Total Trades: 6
  Successful: 6 (100%)
  Failed: 0
  
Volume:
  ETH Spent: 0.012
  $COMPUTE Acquired: 25.0
  
Costs:
  Gas Spent: 0.0008 ETH (~$2)
  Average Gas per Trade: 0.00013 ETH
  
Current Holdings:
  Total ETH: 0.009
  Total $COMPUTE: 25.0
```

### 5.5 On-Chain Verification

You can verify trades on [BaseScan](https://basescan.org):

1. Copy a worker address from the status output
2. Paste into BaseScan search
3. View the "Transactions" tab
4. You should see Uniswap V3 swap transactions

Example:
```
https://basescan.org/address/0x7a3F...9E2D
```

> ✅ **Checkpoint:** Your swarm is running and generating trades!

---

## Step 6: Reclaim Funds

After running for 15-20 minutes and seeing several trades, let's reclaim the funds.

### 6.1 Stop the Swarm

In the terminal running the swarm, press `Ctrl+C`:

```
^C

[yellow]⚠ Swarm stop requested[/yellow]
[dim]Waiting for current operations to complete...[/dim]

Stopping workers:
  ✓ worker_01 stopped
  ✓ worker_02 stopped
  ✓ worker_03 stopped

✓ All workers stopped
```

### 6.2 Reclaim Funds

```bash
python swarm.py reclaim tutorial_swarm
```

**You'll see:**

```
🐝 Reclaiming Swarm: tutorial_swarm

Queen address: 0xYourQueenAddress...
Workers to reclaim: 3

⚠️  This will withdraw ALL funds from workers

Reclaiming:
  [1/3] worker_01 (0x7a3F...9E2D)
         ETH: 0.003 → Queen ✓ (tx: 0x...)
         $COMPUTE: 12.5 → Queen ✓ (tx: 0x...)
         
  [2/3] worker_02 (0x9B4C...1A5F)
         ETH: 0.005 → Queen ✓ (tx: 0x...)
         $COMPUTE: 8.3 → Queen ✓ (tx: 0x...)
         
  [3/3] worker_03 (0x2D8E...7C4B)
         ETH: 0.006 → Queen ✓ (tx: 0x...)
         $COMPUTE: 4.1 → Queen ✓ (tx: 0x...)

═══════════════════════════════════════════════════
  RECLAIM COMPLETE
═══════════════════════════════════════════════════

Summary:
  Total ETH reclaimed: 0.014 ETH
  Total $COMPUTE reclaimed: 24.9 tokens
  Gas spent: 0.0006 ETH
  
Net position change:
  ETH: -0.007 (spent on trades + gas)
  $COMPUTE: +24.9 tokens

Queen wallet balances updated.
```

### 6.3 Verify Queen Wallet

```bash
python bot.py balance
```

You should see:
- Lower ETH balance (trading costs + gas)
- $COMPUTE tokens acquired by workers

### 6.4 Review Trade History

```bash
# Export trade history
python swarm.py export tutorial_swarm --format csv --output tutorial_trades.csv

# View it
cat tutorial_trades.csv
```

---

## Tutorial Complete! 🎉

### What You Accomplished

✅ Created a 3-worker swarm  
✅ Funded workers with 0.021 ETH  
✅ Ran coordinated trading for 15+ minutes  
✅ Generated 6+ trades across 3 wallets  
✅ Successfully reclaimed all funds  

### What You Learned

- Swarm initialization and configuration
- Worker funding from a queen wallet
- Staggered trading strategies
- Real-time monitoring
- Safe fund reclamation

---

## Next Steps

### Immediate

1. **Experiment with different strategies:**
   ```bash
   python swarm.py init --strategy randomized
   ```

2. **Try a larger swarm:**
   ```bash
   python swarm.py init --workers 10 --funding 0.01
   ```

3. **Set up alerts:**
   Edit `swarm_configs/tutorial_swarm.yaml` and add Telegram/webhook alerts

### Advanced

1. **Read the [API Reference](./API_REFERENCE.md)** for programmatic control
2. **Explore [Security Best Practices](./SECURITY.md)** for production deployments
3. **Check the [FAQ](./FAQ.md)** for common questions

### Production Checklist

Before running larger swarms with real money:

- [ ] Read [SECURITY.md](./SECURITY.md) thoroughly
- [ ] Test with small amounts first
- [ ] Set up monitoring and alerts
- [ ] Configure auto-reclaim
- [ ] Set loss limits
- [ ] Document your configuration
- [ ] Have a recovery plan

---

## Troubleshooting

### Issue: "Insufficient funds for gas"

**Solution:**
```bash
# Top up gas reserves
python swarm.py fund tutorial_swarm --top-up-gas --amount 0.002
```

### Issue: "Worker failed to start"

**Solution:**
```bash
# Check worker balance
python swarm.py balance tutorial_swarm

# Fund if needed
python swarm.py fund tutorial_swarm

# Try starting again
python swarm.py start tutorial_swarm
```

### Issue: "Transaction failed"

**Common causes:**
- Network congestion (wait and retry)
- Gas price too low (increase `max_gas_gwei`)
- RPC issues (try different RPC endpoint)

```bash
# Check network status
python swarm.py network-status

# Update gas settings
python swarm.py config tutorial_swarm set max_gas_gwei 1.0
```

### Issue: "Reclaim stuck"

**Solution:**
```bash
# Check pending transactions
python swarm.py pending-txs tutorial_swarm

# Retry with higher gas
python swarm.py reclaim tutorial_swarm --gas-boost 1.5
```

---

## Glossary

| Term | Definition |
|------|------------|
| **Queen** | Main wallet that funds and controls the swarm |
| **Worker** | Individual trading bot in the swarm |
| **Swarm** | Collection of workers working together |
| **Reclaim** | Process of withdrawing funds from workers |
| **Staggered** | Workers start at different times |
| **Cycle** | Complete buy/sell sequence |

---

## Support

- 📖 [Full Documentation](./SWARM_GUIDE.md)
- ❓ [FAQ](./FAQ.md)
- 🔒 [Security Guide](./SECURITY.md)
- 📚 [API Reference](./API_REFERENCE.md)

---

*Congratulations on completing your first swarm!* 🐝
