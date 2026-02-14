# ❓ Swarm Mode - Frequently Asked Questions

Quick answers to common questions about swarm mode.

---

## General Questions

### What is swarm mode?

Swarm mode allows you to run multiple trading bots (wallets) simultaneously as a coordinated group. Instead of managing one bot, you deploy a "swarm" of workers that trade together to generate higher volume and distribute risk.

### Why should I use swarm mode instead of a single bot?

| Single Bot | Swarm Mode |
|------------|------------|
| One trading wallet | Multiple wallets |
| Lower volume | Higher volume |
| Single point of failure | Distributed risk |
| Easier to track | More organic appearance |
| Simpler setup | More scalable |

### How much does it cost to run a swarm?

**Startup Costs:**
- Worker funding: Depends on count × amount per worker
- Gas for funding: ~0.0001 ETH per worker

**Ongoing Costs:**
- Trading gas: ~0.0001 ETH per trade
- Reclaim gas: ~0.0002 ETH per worker

**Example (10 workers, 0.01 ETH each):**
- Initial: 0.1 ETH + 0.001 gas = **0.101 ETH**
- Daily gas (assuming 100 trades): ~0.01 ETH

### What's the minimum amount to start?

**Absolute minimum:** 3 workers × 0.005 ETH = 0.015 ETH  
**Recommended:** 5-10 workers × 0.01 ETH = 0.05-0.1 ETH

### Can I run multiple swarms at once?

Yes! Each swarm has its own configuration and workers:

```bash
python swarm.py init --name swarm_a --workers 5
python swarm.py init --name swarm_b --workers 10

python swarm.py start swarm_a
python swarm.py start swarm_b  # In another terminal
```

---

## Setup & Configuration

### How do I create a swarm?

```bash
# Interactive mode (recommended for beginners)
python swarm.py init

# Or specify options
python swarm.py init --name my_swarm --workers 10 --funding 0.01
```

### Where are swarm files stored?

```
swarm_configs/
├── <swarm_name>.yaml          # Main configuration
└── <swarm_name>/
    ├── workers/
    │   ├── worker_01.enc      # Encrypted private keys
    │   ├── worker_02.enc
    │   └── ...
    └── logs/
        └── *.log              # Worker logs
```

### Can I use the same queen wallet for multiple swarms?

Yes, but be careful about:
- **Nonce conflicts:** If running simultaneously
- **Balance tracking:** Harder to attribute costs
- **Risk concentration:** Single point of failure

**Better approach:** Use different queen wallets per swarm.

### How do I backup my swarm?

```bash
# Backup everything
tar -czf swarm_backup_$(date +%Y%m%d).tar.gz swarm_configs/

# Store securely (these are encrypted but sensitive)
cp swarm_backup_*.tar.gz /secure/backup/location/
```

**Critical files to backup:**
- `swarm_configs/<name>.yaml`
- `swarm_configs/<name>/workers/*.enc`

### How do I change swarm configuration?

```bash
# View current config
python swarm.py config my_swarm show

# Edit specific value
python swarm.py config my_swarm set max_gas_gwei 1.0

# Open in editor
python swarm.py config my_swarm edit
```

### Can I add workers to an existing swarm?

Not directly. You need to:
1. Stop the swarm
2. Reclaim funds
3. Create new swarm with desired worker count
4. Fund and start

```bash
python swarm.py stop my_swarm --reclaim
python swarm.py init --name my_swarm_v2 --workers 15
python swarm.py fund my_swarm_v2
python swarm.py start my_swarm_v2
```

---

## Funding & Reclaiming

### How much should I fund each worker?

**Guidelines:**

| Worker Type | Amount | Duration |
|-------------|--------|----------|
| Test/learning | 0.003-0.005 ETH | 1-2 hours |
| Small scale | 0.01 ETH | 4-8 hours |
| Production | 0.02-0.05 ETH | 1-2 days |

**Formula:**
```
Amount = (Buy_Amount × Sell_After_Buys) + Gas_Reserve
Example: (0.002 × 10) + 0.005 = 0.025 ETH
```

### What happens if a worker runs out of ETH?

The worker will:
1. Log an error
2. Stop trading
3. Remain in "error" state

**Solutions:**
```bash
# Top up specific worker
python swarm.py fund my_swarm --workers worker_05 --amount 0.005

# Top up all low workers
python swarm.py fund my_swarm --top-up-gas
```

### How do I reclaim funds?

```bash
# Full reclaim (all workers, all tokens)
python swarm.py reclaim my_swarm

# Reclaim specific workers
python swarm.py reclaim my_swarm --workers worker_01,worker_02

# Reclaim only ETH
python swarm.py reclaim my_swarm --eth-only

# Stop and reclaim
python swarm.py stop my_swarm --reclaim
```

### What if reclaim fails?

**Check:**
```bash
# See pending transactions
python swarm.py pending-txs my_swarm

# Check worker balances
python swarm.py balance my_swarm
```

**Retry:**
```bash
# Retry failed only
python swarm.py reclaim my_swarm --retry-failed

# With higher gas
python swarm.py reclaim my_swarm --gas-boost 1.5
```

### Can I reclaim automatically?

Yes, configure in `swarm.yaml`:

```yaml
reclaim:
  auto_reclaim:
    enabled: true
    trigger: cycle_complete  # or: profit_threshold, schedule
    
  profit_threshold:
    min_profit_eth: 0.01
    
  schedule:
    - "08:00"
    - "20:00"
```

Or via command line:
```bash
python swarm.py start my_swarm --reclaim-after-cycles 5
python swarm.py start my_swarm --reclaim-at "2025-12-25 00:00:00"
```

---

## Trading & Strategies

### What strategies are available?

| Strategy | Best For | Description |
|----------|----------|-------------|
| `uniform` | Beginners | All workers identical |
| `staggered` | Most users | Workers start at different times |
| `randomized` | Organic look | Random amounts and intervals |
| `wave` | Volume spikes | Coordinated trading waves |

### How do I change strategy?

Edit `swarm.yaml`:

```yaml
strategy:
  type: staggered  # Change this
  config:
    # Strategy-specific settings
```

Or reinitialize:
```bash
python swarm.py init --name my_swarm --strategy randomized
```

### What's the difference between strategies?

**Uniform:**
```
worker_01: Buy 0.002 ETH every 5 min
worker_02: Buy 0.002 ETH every 5 min  ← Same!
worker_03: Buy 0.002 ETH every 5 min
```

**Staggered:**
```
T+0s:   worker_01 starts (buys at 0, 5, 10...)
T+30s:  worker_02 starts (buys at 0.5, 5.5, 10.5...)
T+60s:  worker_03 starts (buys at 1, 6, 11...)
```

**Randomized:**
```
worker_01: Buy 0.001-0.003 ETH every 3-7 min
worker_02: Buy 0.001-0.003 ETH every 3-7 min (different random values)
```

### Can workers have different settings?

Yes, using worker profiles:

```yaml
worker_profiles:
  aggressive:
    buy_amount_eth: 0.005
    buy_interval_minutes: 2
    
  conservative:
    buy_amount_eth: 0.001
    buy_interval_minutes: 10

strategy:
  workers:
    - profile: aggressive
      count: 3
    - profile: conservative
      count: 7
```

### How long should I run a swarm?

**Recommendations:**

| Goal | Duration | Notes |
|------|----------|-------|
| Testing | 15-30 min | Just to verify |
| Daily volume | 8-12 hours | Workday coverage |
| Continuous | 24-48 hours | With monitoring |
| Max volume | 1-2 weeks | Reclaim regularly |

### What happens during a sell cycle?

1. Worker reaches `sell_after_buys` count
2. Executes sell transaction (all $COMPUTE → ETH)
3. Resets buy counter to 0
4. Continues buying
5. Logs cycle completion

```
[worker_01] Buy 9/10 completed
[worker_01] Buy 10/10 completed
[worker_01] 💰 SELLING ALL POSITIONS
[worker_01] ✓ Sell successful! Got 0.021 ETH
[worker_01] Cycle complete! Restarting...
[worker_01] Buy 1/10...
```

---

## Monitoring & Troubleshooting

### How do I check if my swarm is working?

```bash
# Quick status
python swarm.py status my_swarm

# Watch live
python swarm.py status my_swarm --watch

# Check logs
python swarm.py logs my_swarm worker_01 --follow
```

### What do the status symbols mean?

| Symbol | Status | Meaning |
|--------|--------|---------|
| ● | ACTIVE | Trading normally |
| ◐ | PENDING | Starting up |
| ◎ | STOPPED | Gracefully stopped |
| ○ | ERROR | Needs attention |

### Why are my transactions failing?

**Common causes:**

1. **Gas price too low**
   ```bash
   python swarm.py config my_swarm set max_gas_gwei 1.0
   ```

2. **Insufficient ETH for gas**
   ```bash
   python swarm.py fund my_swarm --top-up-gas
   ```

3. **Network congestion**
   - Wait and retry
   - Increase gas limit

4. **RPC issues**
   - Try different RPC endpoint
   - Check connection

### How do I view logs?

```bash
# All workers
python swarm.py logs my_swarm

# Specific worker
python swarm.py logs my_swarm worker_01

# Follow mode (live)
python swarm.py logs my_swarm worker_01 --follow

# Last N lines
python swarm.py logs my_swarm --lines 50

# Since specific time
python swarm.py logs my_swarm --since "2025-01-15 10:00:00"
```

### Can I get alerts?

Yes! Configure in `swarm.yaml`:

```yaml
alerts:
  telegram:
    enabled: true
    bot_token: "YOUR_BOT_TOKEN"
    chat_id: "YOUR_CHAT_ID"
    
  webhook:
    enabled: true
    url: "https://your-server.com/webhook"
    events: ["trade_success", "worker_error", "reclaim_complete"]
```

Or use the dashboard:
```bash
python swarm.py dashboard my_swarm
```

### How do I stop a swarm gracefully?

```bash
# Graceful stop (waits for current trades)
python swarm.py stop my_swarm

# In the running terminal
Ctrl+C

# Force stop (immediate)
python swarm.py stop my_swarm --force
```

### What if I lose my swarm password?

⚠️ **Your worker funds will be lost.** The private keys are encrypted and cannot be recovered without the password.

**Prevention:**
- Store password in password manager
- Reclaim funds regularly
- Keep backups

**Recovery options:**
1. If queen wallet has backup → Create new swarm
2. If workers still have funds → Cannot recover

---

## Security

### Is swarm mode safe?

As safe as the underlying bot, with additional considerations:

- ✅ Private keys are encrypted
- ✅ Each worker is isolated
- ✅ Loss limited to worker balances
- ⚠️ More wallets = more attack surface
- ⚠️ Queen wallet is critical

### How do I keep my swarm secure?

**Essential:**
- [ ] Use dedicated queen wallet
- [ ] Strong encryption password
- [ ] Restrictive file permissions (600)
- [ ] Never commit configs to git
- [ ] Regular backups

**Recommended:**
- [ ] Run on dedicated server/VM
- [ ] Firewall rules
- [ ] Monitor for unusual activity
- [ ] Set loss limits
- [ ] Use hardware wallet for queen

### Can someone steal my funds?

If they gain access to:
- **Worker files alone** → No (encrypted)
- **Worker files + password** → Yes (worker funds only)
- **Queen wallet** → Yes (all funds)

**Mitigation:**
- Strong, unique password
- Secure server
- Regular reclaims
- Limited worker balances

### Should I use a hardware wallet?

**For queen wallet:** Highly recommended for large amounts

**For workers:** Not practical (automated signing needed)

**Setup:**
1. Create queen on hardware wallet
2. Transfer funds to queen
3. Fund swarm from queen
4. Keep hardware wallet offline

---

## Performance & Scaling

### How many workers can I run?

**Practical limits:**

| Setup | Max Workers | Notes |
|-------|-------------|-------|
| Single machine | 10-20 | Resource limits |
| VPS (2 vCPU) | 20-30 | Network limits |
| Dedicated server | 50-100 | RPC rate limits |
| Distributed | 100+ | Multiple RPCs needed |

### How much volume can a swarm generate?

**Example (10 workers):**

| Setting | Daily Volume | Gas Cost |
|---------|--------------|----------|
| 0.002 ETH × 10 buys × 12 cycles | ~$720 | ~$0.07 |
| 0.005 ETH × 10 buys × 12 cycles | ~$1,800 | ~$0.07 |
| 0.01 ETH × 10 buys × 12 cycles | ~$3,600 | ~$0.07 |

### Can I run swarms on multiple servers?

Yes, but each server needs:
- Its own swarm configuration
- Different queen wallet (or careful nonce management)
- Independent monitoring

**Not recommended for beginners.**

### How do I optimize gas costs?

1. **Choose efficient RPC:** Low latency = fewer retries
2. **Set appropriate gas limits:** Not too high, not too low
3. **Trade during low congestion:** Gas prices vary
4. **Batch operations:** Fund/reclaim efficiently

```bash
# Check gas prices
python swarm.py network-status

# Adjust settings
python swarm.py config my_swarm set max_gas_gwei 0.5
```

---

## Advanced

### Can I integrate with my own software?

Yes! Use the Python API:

```python
from swarm_manager import SwarmManager

manager = SwarmManager()
swarm = manager.get_swarm("my_swarm")

# Custom logic
for worker in swarm.workers:
    if worker.balance_eth < 0.001:
        manager.fund_worker(swarm.name, worker.name)
```

See [API Reference](./API_REFERENCE.md) for details.

### Can I run swarms programmatically?

Yes:

```python
from swarm_manager import SwarmManager, StartOptions

manager = SwarmManager()

# Schedule start
import schedule
import time

def start_trading():
    manager.start_swarm("my_swarm")

def stop_and_reclaim():
    manager.stop_swarm("my_swarm")
    manager.reclaim_swarm("my_swarm")

schedule.every().day.at("09:00").do(start_trading)
schedule.every().day.at("17:00").do(stop_and_reclaim)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Can I simulate without real trades?

Yes, use dry-run mode:

```bash
python swarm.py start my_swarm --dry-run
```

Or in config:
```yaml
trading:
  dry_run: true
```

### How do I export data?

```bash
# CSV export
python swarm.py export my_swarm --format csv --output trades.csv

# JSON export
python swarm.py export my_swarm --format json --output trades.json

# Specific date range
python swarm.py export my_swarm \
  --from "2025-01-01" \
  --to "2025-01-31" \
  --format csv
```

---

## Still Have Questions?

- 📖 Read the [Complete Guide](./SWARM_GUIDE.md)
- 🎓 Follow the [Tutorial](./TUTORIAL.md)
- 🔒 Review [Security Guidelines](./SECURITY.md)
- 📚 Check [API Reference](./API_REFERENCE.md)

---

*Last updated: 2025-02-14*
