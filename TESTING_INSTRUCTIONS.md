# Volume Bot - Testing Instructions for Tester Agent

## Current Status (2026-02-15 14:30 UTC)

### ✅ WORKING: BNKR via Aerodrome
- **Branch:** `feature/multidex-fixes`
- **Status:** Tested live, fully functional
- **TX Example:** 0x1aa0b3a5e4475abfe0... (1,572 BNKR acquired)

### 🔄 IN PROGRESS: COMPUTE via V4 (Library Integration)
- **Branch:** `feature/v4-universal-router`
- **Latest Commit:** `899291a`
- **Status:** Library API fixed, needs testing

---

## IMPORTANT: Library API Discovery

**The library API is different than initially assumed.**

### Correct API:
```python
from uniswap_universal_router_decoder import RouterCodec

codec = RouterCodec()
chain = codec.encode.chain()  # Get chain builder

# Add swap to chain
chain.v4_swap_exact_in_single(...)

# Build transaction
tx = codec.build_transaction(chain=chain, ...)
```

### What Was Wrong:
- ❌ `codec.add_wrap_eth()` - Method doesn't exist
- ❌ `codec.add_v4_swap_exact_in_single()` - Method doesn't exist

### What's Fixed:
- ✅ `codec.encode.chain()` - Get chain builder
- ✅ `chain.v4_swap_exact_in_single()` - Add swap to chain
- ✅ `codec.build_transaction()` - Build final TX

---

## COMPUTE V4 Test Instructions

### 1. Prerequisites

```bash
cd /home/fuzzbox/.openclaw/workspace/base-volume-bot
git checkout feature/v4-universal-router
git pull origin feature/v4-universal-router  # Should be at 899291a

# Verify library installed
pip show uniswap-universal-router-decoder  # Should be v2.0.0+
```

### 2. Test Dry-Run First (NEW)

```bash
python bot.py run --dry-run --token-address 0x696381f39F17cAD67032f5f52A4924ce84e51BA3
```

**Expected output:**
```
[yellow][DRY RUN] Testing V4 swap encoding...[/yellow]
[yellow]⚠ [DRY RUN] No V2/V3 pools found, testing V4 Universal Router...[/yellow]
[dim][DRY RUN] Testing V4 transaction encoding...[/dim]
[green]✓ [DRY RUN] V4 library loaded and ready[/green]
[green]✓ [DRY RUN] Routing validation complete[/green]
```

### 3. Test Live (If Dry-Run Passes)

**⚠️ WARNING: Only ~0.0015 ETH remaining**

```bash
python bot.py run --token-address 0x696381f39F17cAD67032f5f52A4924ce84e51BA3
```

**Expected if working:**
```
[dim]Building V4 swap with library...[/dim]
[dim]  Trying fee=500...[/dim]
[green]✓ Found V4 pool: fee=500[/green]
[dim]Transaction built, sending...[/dim]
[green]✓ V4 swap successful![/green]
```

**Then verify:**
```bash
python bot.py balance
# Should show: COMPUTE Balance: > 0
```

---

## If It Still Fails

### Check Library API:
```python
python -c "
from uniswap_universal_router_decoder import RouterCodec
codec = RouterCodec()
print('Methods:', [m for m in dir(codec) if not m.startswith('_')])
print('Encode methods:', [m for m in dir(codec.encode) if not m.startswith('_')])
"
```

### Expected Methods:
- `codec.encode.chain()` - Returns chain builder
- `chain.v4_swap_exact_in_single()` - Add swap
- `codec.build_transaction()` - Build TX

---

## What to Report

### If successful:
- [ ] TX hash
- [ ] Gas used
- [ ] COMPUTE balance after swap
- [ ] Dry-run output

### If failed:
- [ ] Error message (full traceback)
- [ ] Output of library API check above
- [ ] Python version: `python --version`
- [ ] Library version: `pip show uniswap-universal-router-decoder`

---

## Alternative If V4 Keeps Failing

**Recommend focusing on BNKR:**
```bash
git checkout feature/multidex-fixes
python bot.py run --token-address 0x22aF33FE49fD1Fa80c7149773dDe5890D3c76F3b
```

BNKR is proven working via Aerodrome.

---

## Branch Status

| Branch | Status | Action |
|--------|--------|--------|
| `feature/multidex-fixes` | ✅ Ready | BNKR working, can merge |
| `feature/v4-universal-router` | 🔄 Testing | Library API fixed |
| `feature/security-hardening` | ✅ Ready | Security audit complete |
| `feature/docs-improvements` | ✅ Ready | Documentation complete |

---

## Current ETH Balance

- **Approximate:** ~0.0015 ETH
- **Test amount:** 0.0005 ETH per swap
- **Minimum to preserve:** 0.001 ETH
- **Action if low:** Switch to BNKR testing

---

## Quick Reference

### COMPUTE Token
- **Address:** `0x696381f39F17cAD67032f5f52A4924ce84e51BA3`
- **Network:** Base
- **Type:** V4-only

### BNKR Token (Proven Working)
- **Address:** `0x22aF33FE49fD1Fa80c7149773dDe5890D3c76F3b`
- **Router:** Aerodrome
- **Status:** ✅ Fully functional

---

*Last updated: 2026-02-15 14:30 UTC*
*Library API fixed, ready for testing*
