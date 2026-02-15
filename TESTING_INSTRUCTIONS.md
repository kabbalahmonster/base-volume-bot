# Volume Bot - Testing Instructions for Tester Agent

## Current Status (2026-02-15)

### ✅ WORKING: BNKR via Aerodrome
- **Branch:** `feature/multidex-fixes`
- **Status:** Tested live, fully functional
- **TX Example:** 0x1aa0b3a5e4475abfe0... (1,572 BNKR acquired)

### 🔄 READY TO TEST: COMPUTE via V4 (NEW LIBRARY)
- **Branch:** `feature/v4-universal-router`
- **Latest Commit:** `372b7df`
- **Status:** Rewritten with official encoder library

---

## COMPUTE V4 Test Instructions

### 1. Prerequisites

```bash
cd /home/fuzzbox/.openclaw/workspace/base-volume-bot
git fetch origin
git checkout feature/v4-universal-router
git pull origin feature/v4-universal-router  # Should be at 372b7df

# Install NEW dependency
pip install uniswap-universal-router-decoder

# Verify installation
python -c "from uniswap_universal_router_decoder import RouterCodec; print('✓ Library installed')"
```

### 2. Test COMPUTE (Small Amount First)

```bash
# Test with 0.0005 ETH (minimum to verify functionality)
python bot.py run --token-address 0x696381f39F17cAD67032f5f52A4924ce84e51BA3
```

### 3. Expected Output

**If working correctly:**
```
[green]✓ uniswap-universal-router-decoder library loaded[/green]
...
[dim]Building V4 swap with library...[/dim]
[dim]  Trying fee=500, tickSpacing=10...[/dim]
[green]✓ Found V4 pool: fee=500[/green]
[dim]Transaction built, sending...[/dim]
[dim]TX: 0x...[/dim]
[green]✓ V4 swap successful! Gas used: ...[/green]
```

**Then verify:**
```bash
# Check COMPUTE balance
python bot.py balance
# Should show: COMPUTE Balance: > 0
```

### 4. What to Report

If successful:
- [ ] TX hash
- [ ] Gas used
- [ ] COMPUTE balance after swap
- [ ] Any warnings/errors

If failed:
- [ ] Error message
- [ ] TX hash (if any)
- [ ] Logs from console

---

## Architecture Changes

### New Library Integration
- **Library:** `uniswap-universal-router-decoder` (v2.0.0+)
- **Purpose:** Properly encode V4 Universal Router commands
- **Key Features:**
  - `add_wrap_eth()` - ETH → WETH wrapping
  - `add_v4_swap_exact_in_single()` - V4 swap encoding
  - `add_settle()` - Settle output tokens
  - `add_take()` - Take tokens to wallet
  - `add_sweep()` - Clean up remainders

### Why Previous Attempts Failed
1. **Manual encoding** of V4 commands was incorrect
2. **Wrong parameter structure** for V4_SWAP
3. **Missing proper settlement** flow
4. **Library now handles** all complex ABI encoding

---

## Branch Status

| Branch | Status | Action |
|--------|--------|--------|
| `feature/multidex-fixes` | ✅ Ready | BNKR working, can merge to main |
| `feature/v4-universal-router` | 🔄 Testing | COMPUTE with new library |
| `feature/security-hardening` | ✅ Ready | Security audit complete |
| `feature/docs-improvements` | ✅ Ready | Documentation complete |
| `feature/test-suite` | ✅ Ready | Test suite ready |

---

## Post-Test Actions

### If COMPUTE Works:
1. Test a few more swaps to verify reliability
2. Merge `feature/v4-universal-router` to main
3. Update README with COMPUTE support
4. Deploy production bot

### If COMPUTE Still Fails:
1. Document V4 as "experimental"
2. Merge working BNKR branch (`feature/multidex-fixes`)
3. Focus on BNKR volume generation
4. Wait for 0x aggregator V4 support

---

## Current ETH Balance
- **Before testing:** Check wallet
- **Recommended test amount:** 0.0005 ETH per swap
- **Stop if:** Balance drops below 0.001 ETH

---

## Quick Reference

### COMPUTE Token
- **Address:** `0x696381f39F17cAD67032f5f52A4924ce84e51BA3`
- **Network:** Base
- **Type:** V4-only (no V2/V3 pools)

### BNKR Token (Working)
- **Address:** `0x22aF33FE49fD1Fa80c7149773dDe5890D3c76F3b`
- **Router:** Aerodrome
- **Status:** ✅ Fully functional

---

## Support

If issues arise:
1. Check library installed: `pip show uniswap-universal-router-decoder`
2. Verify branch: `git log --oneline -1` (should show 372b7df)
3. Check Python version: `python --version` (3.9+ required)
4. Report full error output

---

*Last updated: 2026-02-15 14:18 UTC*
*New V4 library integration ready for testing*
