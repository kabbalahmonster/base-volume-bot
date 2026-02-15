# V4 Trading Module - Bug Summary & Fix Checklist

## Overview

This document provides a quick reference for all bugs and issues found during the audit. Use this checklist when implementing fixes.

---

## 🔴 CRITICAL BUGS (Must Fix)

### BUG-001: Wrong V4_SWAP Command Byte
- **Severity:** Critical
- **File:** `encoding.py`, `universal_router.py`
- **Current:** `0x30`
- **Correct:** `0x10`
- **Fix:**
  ```python
  # In encoding.py line 120
  V4_SWAP = 0x10  # Changed from 0x30
  ```

### BUG-002: Wrong PERMIT2_TRANSFER_FROM Command Byte
- **Severity:** Critical
- **File:** `encoding.py`, `universal_router.py`
- **Current:** `0x0c`
- **Correct:** `0x02`
- **Fix:**
  ```python
  PERMIT2_TRANSFER_FROM = 0x02  # Changed from 0x0c
  ```

### BUG-003: Wrong UNWRAP_WETH Command Byte
- **Severity:** Critical
- **File:** `encoding.py`, `universal_router.py`
- **Current:** `0x0d`
- **Correct:** `0x0c`
- **Fix:**
  ```python
  UNWRAP_WETH = 0x0c  # Changed from 0x0d
  ```

### BUG-004: V4 Swap Encoding Completely Wrong
- **Severity:** Critical
- **File:** `encoding.py` (lines 120-198)
- **Issue:** Using V3-style encoding instead of V4 Actions pattern
- **Fix Required:** Rewrite encode_v4_swap() to use Actions encoding

---

## 🟠 HIGH SEVERITY BUGS

### BUG-005: Pool ID Calculation Unverified
- **Severity:** High
- **File:** `pool_manager.py` (lines 95-99)
- **Issue:** Pool ID encoding may not match Solidity implementation
- **Fix:** Test against known pool IDs on-chain

### BUG-006: Hardcoded Gas Limits
- **Severity:** High
- **File:** Multiple
- **Issue:** Fixed gas limits won't adapt to network conditions
- **Fix:** Implement dynamic gas estimation

### BUG-007: Missing Revert Flag Support
- **Severity:** High
- **File:** `universal_router.py`
- **Issue:** Not using command byte structure properly
- **Fix:** Support allow_revert flag in command encoding

---

## 🟡 MEDIUM SEVERITY BUGS

### BUG-008: min_amount_out Hardcoded to 0
- **Severity:** Medium
- **File:** `universal_router.py` (lines 181, 277)
- **Issue:** `min_amount_out=0` means no slippage protection
- **Fix:** Calculate from expected output and slippage percent

### BUG-009: Exception Handling Too Broad
- **Severity:** Medium
- **File:** All modules
- **Issue:** Catches all exceptions including system ones
- **Fix:** Catch specific exceptions only

### BUG-010: Missing Deadline Validation
- **Severity:** Medium
- **File:** `universal_router.py`
- **Issue:** No validation of deadline parameter
- **Fix:** Add assertions for deadline range

### BUG-011: Decimal Precision May Be Insufficient
- **Severity:** Medium
- **File:** `quoter.py`
- **Issue:** Default Decimal context may lose precision for large numbers
- **Fix:** Increase precision in calculations

---

## 🟢 LOW SEVERITY BUGS

### BUG-012: Unused Variable in sell()
- **Severity:** Low
- **File:** `__init__.py` (line 138)
- **Issue:** `amount_in_wei` computed but not passed to router
- **Fix:** Remove or use the variable

### BUG-013: Missing Address Validation
- **Severity:** Low
- **File:** `encoding.py` (line 289)
- **Issue:** `_is_zero_for_one()` doesn't validate addresses
- **Fix:** Add checksum validation

### BUG-014: Unused token_decimals in buy()
- **Severity:** Low
- **File:** `__init__.py` (line 184)
- **Issue:** Variable computed but unused
- **Fix:** Remove or use for validation

### BUG-015: No Support for Permit2 Signatures
- **Severity:** Low
- **Feature Gap:** Only supports ERC20 + Permit2 allowance pattern
- **Fix:** Add optional permit signature support for gas savings

---

## Quick Fix Script

```python
#!/usr/bin/env python3
"""
Quick fix script for critical bugs.
Run this after reviewing the changes.
"""

import re

def fix_file(filepath, replacements):
    """Apply replacements to a file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Fixed: {filepath}")

# Fix encoding.py
fix_file('encoding.py', [
    ("'V4_SWAP': 0x30", "'V4_SWAP': 0x10"),
    ("'PERMIT2_TRANSFER_FROM': 0x0c", "'PERMIT2_TRANSFER_FROM': 0x02"),
    ("'UNWRAP_WETH': 0x0d", "'UNWRAP_WETH': 0x0c"),
    ("PERMIT2_TRANSFER_FROM = 0x0c", "PERMIT2_TRANSFER_FROM = 0x02"),
    ("UNWRAP_WETH = 0x0d", "UNWRAP_WETH = 0x0c"),
    ("V4_SWAP = 0x30", "V4_SWAP = 0x10"),
])

# Fix universal_router.py
fix_file('universal_router.py', [
    ("'PERMIT2_TRANSFER_FROM': 0x0c", "'PERMIT2_TRANSFER_FROM': 0x02"),
    ("'UNWRAP_WETH': 0x0d", "'UNWRAP_WETH': 0x0c"),
    ("'V4_SWAP': 0x30", "'V4_SWAP': 0x10"),
])

print("\nCritical bugs fixed!")
print("NOTE: V4 swap encoding still needs manual rewrite.")
print("See TEST_RECOMMENDATIONS.md for correct implementation.")
```

---

## Files to Modify

| File | Lines | Priority |
|------|-------|----------|
| `encoding.py` | 120-198, 289-307 | Critical |
| `universal_router.py` | 36-45, 181, 277, 311 | Critical |
| `pool_manager.py` | 95-99 | High |
| `quoter.py` | 55-68 | Medium |
| `__init__.py` | 101, 138, 184 | Low |

---

## Testing After Fixes

```bash
# 1. Run unit tests
python -m pytest tests/test_v4_module.py -v

# 2. Test pool ID calculation
python -c "
from v4_trading.pool_manager import V4PoolManager
from web3 import Web3
w3 = Web3()
pm = V4PoolManager(w3, '0x...')
# Verify against known pool
print(pm.get_pool_id('...', '...', 3000))
"

# 3. Test command encoding
python -c "
from v4_trading.encoding import Commands
assert Commands.V4_SWAP == 0x10
assert Commands.PERMIT2_TRANSFER_FROM == 0x02
assert Commands.UNWRAP_WETH == 0x0c
print('Command bytes correct!')
"

# 4. Integration test (requires Base connection)
python -c "
from web3 import Web3
from v4_trading import V4Trader
w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))
print(f'Connected: {w3.is_connected()}')
# Add more tests...
"
```

---

## Success Criteria

The module is ready for production when:

- [ ] All command bytes match Uniswap spec
- [ ] V4 swap encoding uses correct Actions pattern
- [ ] Pool ID calculation verified against on-chain pools
- [ ] Gas estimation is dynamic
- [ ] All unit tests pass
- [ ] Integration test with small swap succeeds
- [ ] COMPUTE pool price matches expected range

---

## References

- **Audit Report:** `AUDIT_REPORT.md`
- **Test Recommendations:** `tests/TEST_RECOMMENDATIONS.md`
- **Uniswap Docs:** https://docs.uniswap.org/contracts/v4/overview
- **Universal Router Commands:** https://docs.uniswap.org/contracts/universal-router/technical-reference

---

**Version:** 1.0  
**Generated:** 2026-02-15  
**Status:** Ready for fixes
