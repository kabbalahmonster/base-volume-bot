# Uniswap V4 Trading Module - Functionality Audit Report

**Date:** 2026-02-15  
**Auditor:** OpenClaw Subagent  
**Branch:** feature/uniswap-v4-module  
**Files Audited:** 5 modules, ~2,351 lines

---

## Executive Summary

The V4 Trading Module provides a reusable interface for Uniswap V4 swaps on Base. While the overall architecture is sound, **CRITICAL ISSUES** were found in command encoding that would prevent swaps from executing. Several other issues ranging from medium to low severity were also identified.

### Overall Grade: **C+ (NEEDS FIXES BEFORE PRODUCTION)**

| Category | Grade | Notes |
|----------|-------|-------|
| Pool ID Calculation | B+ | Minor encoding issue |
| Price Conversions | B | Correct formula but potential overflow |
| Command Encoding | **F** | **Critical: Wrong command bytes** |
| Slippage Logic | B | Correct calculation |
| Token Decimals | A | Properly handled |
| WETH Operations | B | Logic correct but needs validation |
| Permit2 | B- | Missing signature-based permits |
| Error Handling | C+ | Generic exception catching |
| Gas Estimation | D | Hardcoded values |

---

## 1. Critical Issues (Must Fix)

### 🔴 ISSUE-001: Incorrect V4_SWAP Command Byte

**Location:** `encoding.py` line 120, `universal_router.py` line 36

**Current (WRONG):**
```python
'V4_SWAP': 0x30,  # Actually 0x10 per official docs
```

**Expected (CORRECT):**
```python
'V4_SWAP': 0x10,  # Per Uniswap Universal Router v2 spec
```

**Impact:** Any swap transaction will revert with `InvalidCommandType`  
**Reference:** https://docs.uniswap.org/contracts/universal-router/technical-reference

**Official Command Mapping:**
| Command | Current | Correct |
|---------|---------|---------|
| V4_SWAP | 0x30 | **0x10** |
| PERMIT2_PERMIT | 0x0a | ✓ 0x0a |
| PERMIT2_TRANSFER_FROM | 0x0c | **0x02** |
| WRAP_ETH | 0x0b | ✓ 0x0b |
| UNWRAP_WETH | 0x0d | **0x0c** |
| SWEEP | 0x04 | ✓ 0x04 |
| PAY_PORTION | 0x06 | ✓ 0x06 |

---

### 🔴 ISSUE-002: Missing V4 Actions Encoding

**Location:** `encoding.py` - `encode_v4_swap()`

The current encoding is **completely incorrect** for V4. V4 swaps use an "actions" pattern:

```solidity
// Correct V4 swap structure:
- bytes actions      // Action identifiers (SWAP_EXACT_IN, SETTLE, TAKE)
- bytes[] params     // ABI-encoded params for each action
```

**Actions Constants (from v4-periphery):**
```python
class V4Actions:
    SWAP_EXACT_IN = 0x04
    SWAP_EXACT_OUT = 0x05
    SETTLE = 0x06
    SETTLE_ALL = 0x07
    TAKE = 0x08
    TAKE_ALL = 0x09
    TAKE_PORTION = 0x0a
```

**Current incorrect encoding:**
```python
# WRONG - this is V3-style encoding
encode(['bytes32', 'bool', 'int256', 'uint160', 'address'], ...)
```

**Correct encoding should be:**
```python
# Step 1: Encode swap action
swap_params = encode(
    ['address', 'uint256', 'uint256', 'bytes'],
    [recipient, amount_in, min_amount_out, path]
)
actions = bytes([V4Actions.SWAP_EXACT_IN])
params = [swap_params]

# Step 2: Encode settle action (input token payment)
settle_params = encode(['address', 'uint256'], [token_in, amount_in])
actions += bytes([V4Actions.SETTLE])
params.append(settle_params)

# Step 3: Encode take action (output token receipt)
take_params = encode(['address', 'address', 'uint256'], [token_out, recipient, min_amount_out])
actions += bytes([V4Actions.TAKE])
params.append(take_params)

# Final encoding for V4_SWAP command
final_input = encode(['bytes', 'bytes[]'], [actions, params])
```

---

## 2. High Severity Issues

### 🟠 ISSUE-003: Pool ID Encoding Format

**Location:** `pool_manager.py` line 95-99

**Current:**
```python
encoded = encode(
    ['address', 'address', 'uint24', 'int24', 'address'],
    [token0, token1, fee, tick_spacing, hooks]
)
```

**Issue:** In Solidity, PoolKey is a struct that may have different packing than ABI-encoded tuple. The Solidity implementation uses:

```solidity
assembly ("memory-safe") {
    poolId := keccak256(poolKey, 0xa0)  // 0xa0 = 160 bytes = 5 * 32
}
```

**Verification Needed:** Compare computed pool ID against actual COMPUTE pool:
- Documented: `0x40332cd73d9c79b34aa477cbd7e6962387dcfda042a12c72ad94bc58262023bf`
- Computed: Run test to verify match

**Recommended:** Add integration test to verify against known pool IDs on-chain.

---

### 🟠 ISSUE-004: Missing Revert Flag Handling

**Location:** `universal_router.py`

Universal Router command bytes include a revert flag in the high bit:

```
Bit structure: f r r c c c c c
- f (bit 7): Allow revert flag (1 = can revert without failing tx)
- r (bits 5-6): Reserved
- c (bits 0-4): Command identifier
```

**Current code doesn't handle this:**
```python
commands.append(COMMANDS['V4_SWAP'])  # Just 0x10
# Should be: 0x10 | 0x80 if allowing partial fills
```

**Recommendation:** Add optional `allow_revert` parameter to commands.

---

### 🟠 ISSUE-005: Incorrect V4 Swap Input Structure

**Location:** `universal_router.py` - `swap_exact_in()` and `swap_exact_out()`

The current implementation uses a simplified approach that won't work with V4:

```python
# Current (INCORRECT) flow:
1. WRAP_ETH
2. V4_SWAP (wrong encoding)
3. SWEEP
```

**Correct V4 Flow for ETH -> Token:**
```python
1. WRAP_ETH (if needed) - 0x0b
2. V4_SWAP with actions:
   - SWAP_EXACT_IN (0x04) - swap WETH for token
   - SETTLE_ALL (0x07) - pay input from router balance
   - TAKE_ALL (0x09) - receive output to recipient
```

---

## 3. Medium Severity Issues

### 🟡 ISSUE-006: Missing `payerIsUser` Handling

**Location:** `universal_router.py`

For Permit2 transfers, the router needs to know if the user or router is paying:

```python
# Current: No payerIsUser flag
# Correct: Should encode payerIsUser for V4 swaps
```

**Reference:** V3 swaps include `payerIsUser` bool in params.

---

### 🟡 ISSUE-007: sqrtPriceX96 Decimal Precision Loss

**Location:** `quoter.py` line 55-68

**Current:**
```python
sqrt_price = Decimal(sqrt_price_x96) / Decimal(self.Q96)
price = sqrt_price ** 2
```

**Issue:** Python's Decimal with default context may lose precision for large sqrtPriceX96 values (uint160 max ~ 1.4e48).

**Recommendation:**
```python
from decimal import Decimal, getcontext
getcontext().prec = 80  # Increase precision
```

---

### 🟡 ISSUE-008: Quote Calculation Simplified

**Location:** `quoter.py` line 136-164

The quote calculation is oversimplified:

```python
# Current (approximate):
amount_out_decimal = amount_in_decimal * price * (1 - Decimal(fee))
```

**Issue:** This doesn't account for:
- Price impact based on pool liquidity
- Tick-crossing behavior
- Actual V4 swap math

**Recommendation:** Add disclaimer that quotes are estimates, or implement proper V4 swap simulation.

---

### 🟡 ISSUE-009: Missing Deadline Validation

**Location:** `universal_router.py`

```python
if deadline is None:
    deadline = self.w3.eth.get_block('latest')['timestamp'] + 300
```

**Issue:** No validation that deadline is in the future or reasonable.

**Recommendation:**
```python
assert deadline > current_timestamp, "Deadline must be in the future"
assert deadline < current_timestamp + 3600, "Deadline too far in future"
```

---

### 🟡 ISSUE-010: Hardcoded Gas Limits

**Location:** Multiple files

```python
'gas': 500000,  # Hardcoded
'gas': 100000,  # Hardcoded
'gas': 200000,  # Hardcoded
```

**Issue:** Gas costs vary based on:
- Base network conditions
- Swap complexity (ticks crossed)
- Token transfer costs (some tokens are expensive)

**Recommendation:** Use `estimate_gas()` with fallback:
```python
try:
    gas = tx.estimate_gas({'from': account.address})
    gas = int(gas * 1.2)  # 20% buffer
except:
    gas = 500000  # fallback
```

---

## 4. Low Severity Issues

### 🟢 ISSUE-011: Missing `min_amount_out` Calculation

**Location:** `universal_router.py` line 181

```python
min_amount_out=0,  # Should compute from slippage
```

**Recommendation:** Use quoter to get expected output, then apply slippage:
```python
expected_out = quoter.quote_exact_input(...)
min_amount_out = int(expected_out * (1 - slippage_percent / 100))
```

---

### 🟢 ISSUE-012: Exception Handling Too Broad

**Location:** All modules

```python
try:
    # ... code
except Exception as e:
    return False, f"Error: {e}"
```

**Issue:** Catches everything including `KeyboardInterrupt`, `SystemExit`, etc.

**Recommendation:**
```python
except (ContractLogicError, ValueError, Web3Exception) as e:
    return False, f"Swap failed: {e}"
```

---

### 🟢 ISSUE-013: Missing `zeroForOne` Validation

**Location:** `encoding.py`

```python
def _is_zero_for_one(self, token_in, token_out) -> bool:
    return int(token_in, 16) < int(token_out, 16)
```

**Issue:** Should validate addresses are checksummed first.

**Recommendation:**
```python
token_in = self.w3.to_checksum_address(token_in)
token_out = self.w3.to_checksum_address(token_out)
```

---

### 🟢 ISSUE-014: No Support for Permit2 Signatures

**Location:** `universal_router.py`

Current implementation only uses ERC20 approvals then Permit2 allowances. Missing support for signature-based permits which save gas.

**Recommendation:** Add optional permit signature parameter.

---

### 🟢 ISSUE-015: Unused Import and Variables

**Location:** `__init__.py`

```python
amount_in_wei = int(Decimal(str(amount_tokens)) * (10 ** token_decimals))
# Computed but never used - should be passed to router
```

---

## 5. COMPUTE Pool Specifics

### Pool Details
- **Pool ID:** `0x40332cd73d9c79b34aa477cbd7e6962387dcfda042a12c72ad94bc58262023bf`
- **Fee Tier:** 3000 (0.3%)
- **Tick Spacing:** 60 (from FEE_TO_TICK_SPACING)

### Verification Checklist:
- [ ] Pool ID calculation matches on-chain value
- [ ] get_slot0() returns valid data for COMPUTE pool
- [ ] Price calculations match expected range

---

## 6. Test Coverage Assessment

### Current State: **NO TESTS IMPLEMENTED**

No test files exist for the V4 trading module.

### Recommended Test Structure:

```
v4_trading/tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── test_pool_manager.py           # Pool ID and state tests
├── test_encoding.py               # Command encoding tests
├── test_quoter.py                 # Price calculation tests
├── test_universal_router.py       # Swap execution tests
├── test_integration.py            # End-to-end tests
└── test_edge_cases.py             # Edge case scenarios
```

---

## 7. Detailed Findings by File

### `__init__.py` (V4Trader API)

| Line | Issue | Severity |
|------|-------|----------|
| 138 | Unused `amount_in_wei` variable | Low |
| 101 | Generic exception handling | Medium |
| 140-145 | Should pass computed `amount_in_wei` to router | Medium |
| 184 | `token_decimals` computed but unused in quote | Low |

### `pool_manager.py`

| Line | Issue | Severity |
|------|-------|----------|
| 95-99 | Pool ID encoding format needs verification | High |
| 108-109 | Bytes padding logic may be off by one | Low |
| 137 | Pool existence check catches all exceptions | Medium |
| 191 | Hardcoded gas limit | Medium |

### `encoding.py`

| Line | Issue | Severity |
|------|-------|----------|
| 120 | **V4_SWAP command wrong (0x30 vs 0x10)** | **Critical** |
| 159-169 | encode_v4_swap() structure completely wrong | **Critical** |
| 172-198 | encode_v4_swap_exact_in() uses V3 encoding | **Critical** |
| 289-290 | _is_zero_for_one() missing address validation | Low |
| 306-307 | Command constants mostly wrong | **Critical** |

### `quoter.py`

| Line | Issue | Severity |
|------|-------|----------|
| 55-68 | Decimal precision may be insufficient | Medium |
| 136-164 | Quote calculation is approximate | Medium |
| 179-184 | Slippage calculation correct | ✓ |
| 212-214 | Tick math import at function level | Low |

### `universal_router.py`

| Line | Issue | Severity |
|------|-------|----------|
| 36-45 | Command constants wrong | **Critical** |
| 127-132 | _approve_token() has race condition | Medium |
| 181 | min_amount_out hardcoded to 0 | Medium |
| 190 | Command sequence won't work with V4 | **Critical** |
| 277 | min_amount_out hardcoded to 0 | Medium |
| 311-316 | Hardcoded gas limits | Medium |

---

## 8. Recommendations Summary

### Immediate (Before Any Use):
1. **Fix command bytes** per official Uniswap documentation
2. **Rewrite V4 swap encoding** using correct Actions pattern
3. **Verify Pool ID calculation** against known pools

### Short Term (Before Production):
4. Implement proper gas estimation
5. Add comprehensive test suite
6. Improve error handling specificity
7. Add deadline validation
8. Calculate min_amount_out from slippage

### Long Term:
9. Implement signature-based Permit2 permits
10. Add price impact calculations
11. Support multi-hop routing
12. Add event logging and transaction monitoring

---

## 9. Test Implementation Plan

### Unit Tests (Priority 1)

```python
# test_pool_manager.py
def test_pool_id_calculation():
    """Verify Pool ID matches known COMPUTE pool."""
    
def test_slot0_decoding():
    """Test slot0 data structure parsing."""
    
def test_tick_spacing_mapping():
    """Verify FEE_TO_TICK_SPACING values."""

# test_encoding.py
def test_command_bytes():
    """Verify command bytes match Uniswap spec."""
    
def test_v4_swap_encoding():
    """Test V4 swap action encoding."""
    
def test_permit2_encoding():
    """Test Permit2 transfer encoding."""

# test_quoter.py
def test_sqrt_price_x96_conversion():
    """Test price <-> sqrtPriceX96 roundtrip."""
    
def test_slippage_calculation():
    """Verify slippage math."""
    
def test_tick_math():
    """Test tick <-> sqrtPriceX96 conversions."""
```

### Integration Tests (Priority 2)

```python
# test_integration.py
def test_compute_pool_read():
    """Read actual COMPUTE pool data from Base."""
    
def test_eth_to_token_quote():
    """Get quote for ETH->COMPUTE swap."""
    
def test_token_to_eth_quote():
    """Get quote for COMPUTE->ETH swap."""
```

### Edge Cases (Priority 3)

- Zero liquidity pools
- Extreme price ratios
- Very small/large amounts
- Tokens with non-standard decimals (< 6 or > 18)
- Reverted transactions with permit failures

---

## 10. Documentation Corrections

### README.md Issues:
1. Command byte documentation is wrong
2. Missing note that module is not yet production-ready
3. No warning about known issues

---

## Appendix: Corrected Command Constants

```python
# From https://docs.uniswap.org/contracts/universal-router/technical-reference

class Commands:
    # V3/V2 swaps
    V3_SWAP_EXACT_IN = 0x00
    V3_SWAP_EXACT_OUT = 0x01
    V2_SWAP_EXACT_IN = 0x08
    V2_SWAP_EXACT_OUT = 0x09
    
    # Permit2
    PERMIT2_TRANSFER_FROM = 0x02          # Was 0x0c (WRONG)
    PERMIT2_PERMIT_BATCH = 0x03
    PERMIT2_PERMIT = 0x0a                 # Same
    PERMIT2_TRANSFER_FROM_BATCH = 0x0d
    
    # Payments
    SWEEP = 0x04                          # Same
    TRANSFER = 0x05
    PAY_PORTION = 0x06                    # Same
    BALANCE_CHECK_ERC20 = 0x0e
    
    # WETH
    WRAP_ETH = 0x0b                       # Same
    UNWRAP_WETH = 0x0c                    # Was 0x0d (WRONG)
    
    # V4
    V4_SWAP = 0x10                        # Was 0x30 (WRONG)
    V4_INITIALIZE_POOL = 0x13
    V4_POSITION_MANAGER_CALL = 0x14
    
    # Sub-plan
    EXECUTE_SUB_PLAN = 0x21
```

---

**END OF AUDIT REPORT**

*This report should be reviewed by the development team and all critical issues resolved before deploying to production.*
