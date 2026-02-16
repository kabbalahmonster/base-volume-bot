# Troubleshooting Guide

## Common Issues & Solutions

### 🔴 "No Route Found" (0x API)

**Error:**
```
0x API error: 404 - {"message":"no Route matched with those values"}
```

**Cause:**
- Token has insufficient liquidity on 0x
- 0x doesn't have a route for this token pair
- Amount too small for routing

**Solutions:**
1. **Use V3 router instead:**
   ```bash
   python bot.py run --router v3
   ```

2. **Increase buy amount** (0x has minimums)

3. **Check token liquidity** on BaseScan

---

### 🔴 "Nonce too low"

**Error:**
```
nonce too low: next nonce 31, tx nonce 30
```

**Cause:**
- Transaction submitted with stale nonce
- Previous transaction not yet mined
- RPC lag

**Solutions:**
1. **Wait 10-15 seconds** and retry

2. **Check transaction status:**
   ```bash
   python bot.py balance
   ```

3. **For swarms:** Ensure funding uses 'pending' nonce (fixed in main)

---

### 🔴 "Insufficient allowance"

**Error:**
```
Token allowance insufficient for swap
```

**Cause:**
- Token approval not set
- Wrong spender approved
- Approval transaction failed

**Solutions:**
1. **Check approval succeeded:**
   - Look for approval TX in logs
   - Verify on BaseScan

2. **For 0x sells:** Ensure approval goes to correct spender from quote

3. **Manual approval:**
   ```python
   # Approve Max
   token.approve(spender, 2**256-1)
   ```

---

### 🔴 "Out of gas"

**Error:**
```
Transaction ran out of gas
```

**Cause:**
- Gas limit too low for complex swap
- Network congestion
- Uniswap V3 multi-hop swap

**Solutions:**
1. **Increase gas limit in config:**
   ```json
   "max_gas_gwei": 1.0
   ```

2. **Check gas prices:**
   ```bash
   # View current gas
   curl https://base.llamarpc.com -X POST \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1}'
   ```

---

### 🔴 "Insufficient ETH balance"

**Error:**
```
Main wallet needs 0.0118 ETH, has 0.0028 ETH
```

**Cause:**
- Not enough ETH for trade + gas
- Gas reserve too high for small trades

**Solutions:**
1. **Reduce gas reserve in config:**
   ```json
   "funder_gas_reserve": 0.001
   ```

2. **Fund wallet with more ETH:**
   - Minimum: 0.01 ETH for single wallet
   - Recommended: 0.05 ETH

3. **Reduce trade size:**
   ```json
   "buy_amount": 0.0002
   ```

---

### 🔴 "CheckSum address validation error"

**Error:**
```
web3.exceptions.ValidationError: Address has an invalid EIP-55 checksum
```

**Cause:**
- Address not checksummed
- 0x API returns lowercase addresses

**Solution:**
- Already fixed in main - all addresses are checksummed before use

---

### 🔴 "Cannot decrypt wallet"

**Error:**
```
Failed to decrypt wallet. Wrong password?
```

**Cause:**
- Wrong password
- Corrupted wallet file
- Wrong wallet file

**Solutions:**
1. **Verify password** (check backup file if exists)

2. **Check wallet file:**
   ```bash
   ls -la .wallet.enc
   ```

3. **Re-run setup** if needed (generates new wallet)

---

### 🔴 "RPC connection failed"

**Error:**
```
Failed to connect to any RPC
```

**Cause:**
- Network issues
- RPC endpoint down
- Rate limited

**Solutions:**
1. **Check internet connection**

2. **Try different RPC:**
   ```json
   "rpc_url": "https://mainnet.base.org"
   ```

3. **Wait and retry** (RPC may be temporarily down)

---

## Dry Run Testing

Always test before live trading:

```bash
# Single wallet
python bot.py run --dry-run

# Swarm
python swarm_cli.py run --dry-run
```

**What dry-run does:**
- Shows what WOULD happen
- No real transactions
- Validates config
- Estimates costs

---

## Emergency Procedures

### Stop Bot Immediately

Press `Ctrl+C` - bot will:
- Stop after current operation
- Show final stats
- Save state

### Recover Funds Fast

```bash
# Sell all tokens
python bot.py liquidate

# Or withdraw everything
python bot.py withdraw 0xYourAddress --compute
```

### Check Transaction Status

```bash
# Get TX hash from logs
# Check on BaseScan:
open https://basescan.org/tx/0xYourTxHash
```

---

## Debug Mode

Enable verbose logging:

```json
{
  "log_level": "DEBUG"
}
```

**Log files:**
- `volume_bot.log` - Detailed logs
- `swarm_audit.log` - Swarm operations

---

## Still Stuck?

1. Check `FINAL_AUDIT.md` for known issues
2. Review recent commits for fixes
3. Test with `--dry-run` first
4. Start with minimal amounts

**Never trade more than you can afford to lose!**
