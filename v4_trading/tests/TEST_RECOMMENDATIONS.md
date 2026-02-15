# V4 Trading Module - Test Recommendations & Implementation Guide

## Quick Start for Testing

```bash
# Install dependencies
cd /home/fuzzbox/.openclaw/workspace/volume_bot
pip install pytest web3 eth-account eth-abi

# Run tests
cd v4_trading
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_v4_module.py::TestPoolManager -v
python -m pytest tests/test_v4_module.py::TestEncoding -v
python -m pytest tests/test_v4_module.py::TestQuoter -v

# Run with coverage
pip install pytest-cov
python -m pytest tests/ --cov=v4_trading --cov-report=html
```

---

## Priority Order for Fixes

### 🔴 CRITICAL - Fix Before Any Testing (Blocks All Swaps)

1. **Fix Command Constants** (`encoding.py` lines 306-307, `universal_router.py` lines 36-45)
   ```python
   # CORRECT values per Uniswap docs:
   V4_SWAP = 0x10                    # Was 0x30
   PERMIT2_TRANSFER_FROM = 0x02      # Was 0x0c
   UNWRAP_WETH = 0x0c                # Was 0x0d
   ```

2. **Rewrite V4 Swap Encoding** (`encoding.py` lines 120-169)
   - Must use Actions pattern
   - See example below

### 🟠 HIGH - Fix Before Production Use

3. **Verify Pool ID Calculation** against known pools
4. **Add proper gas estimation** (don't use hardcoded values)
5. **Implement correct swap flow** for Universal Router

### 🟡 MEDIUM - Fix Before Heavy Usage

6. **Calculate min_amount_out from slippage**
7. **Add deadline validation**
8. **Improve error handling specificity**

### 🟢 LOW - Nice to Have

9. **Support Permit2 signatures**
10. **Add event logging**

---

## Correct V4 Swap Encoding Example

The current implementation is completely wrong. Here's the correct structure:

```python
# v4_trading/encoding.py

class V4Actions:
    """Action identifiers for V4 swaps."""
    SWAP_EXACT_IN = 0x04
    SWAP_EXACT_OUT = 0x05
    SETTLE = 0x06
    SETTLE_ALL = 0x07
    TAKE = 0x08
    TAKE_ALL = 0x09
    TAKE_PORTION = 0x0a


def encode_v4_swap_exact_in(
    self,
    pool_key: dict,  # {currency0, currency1, fee, tickSpacing, hooks}
    amount_in: int,
    min_amount_out: int,
    recipient: str,
    zero_for_one: bool
) -> tuple:
    """
    Encode V4 swap with actions pattern.
    
    Returns:
        (actions_bytes, params_list) for V4_SWAP command
    """
    from eth_abi import encode
    
    actions = b''
    params = []
    
    # Action 1: SWAP_EXACT_IN
    # params: (poolKey, zeroForOne, amountIn, minAmountOut, hookData)
    swap_params = encode(
        ['(address,address,uint24,int24,address)', 'bool', 'uint256', 'uint256', 'bytes'],
        [
            (
                pool_key['currency0'],
                pool_key['currency1'],
                pool_key['fee'],
                pool_key['tickSpacing'],
                pool_key['hooks']
            ),
            zero_for_one,
            amount_in,
            min_amount_out,
            b''  # hookData
        ]
    )
    actions += bytes([V4Actions.SWAP_EXACT_IN])
    params.append(swap_params)
    
    # Action 2: SETTLE_ALL (pay input token)
    # params: (token, maxAmount)
    input_token = pool_key['currency0'] if zero_for_one else pool_key['currency1']
    settle_params = encode(
        ['address', 'uint256'],
        [input_token, amount_in]
    )
    actions += bytes([V4Actions.SETTLE_ALL])
    params.append(settle_params)
    
    # Action 3: TAKE_ALL (receive output token)
    # params: (token, minAmount)
    output_token = pool_key['currency1'] if zero_for_one else pool_key['currency0']
    take_params = encode(
        ['address', 'uint256'],
        [output_token, min_amount_out]
    )
    actions += bytes([V4Actions.TAKE_ALL])
    params.append(take_params)
    
    return actions, params
```

---

## Corrected Universal Router Commands

```python
# v4_trading/universal_router.py

COMMANDS = {
    # Swaps
    'V3_SWAP_EXACT_IN': 0x00,
    'V3_SWAP_EXACT_OUT': 0x01,
    'V2_SWAP_EXACT_IN': 0x08,
    'V2_SWAP_EXACT_OUT': 0x09,
    
    # Permit2
    'PERMIT2_TRANSFER_FROM': 0x02,      # FIXED
    'PERMIT2_PERMIT_BATCH': 0x03,
    'PERMIT2_PERMIT': 0x0a,
    'PERMIT2_TRANSFER_FROM_BATCH': 0x0d,
    
    # Payments
    'SWEEP': 0x04,
    'TRANSFER': 0x05,
    'PAY_PORTION': 0x06,
    'BALANCE_CHECK_ERC20': 0x0e,
    
    # WETH
    'WRAP_ETH': 0x0b,
    'UNWRAP_WETH': 0x0c,                # FIXED
    
    # V4
    'V4_SWAP': 0x10,                    # FIXED
    'V4_INITIALIZE_POOL': 0x13,
    'V4_POSITION_MANAGER_CALL': 0x14,
    
    # Sub-plan
    'EXECUTE_SUB_PLAN': 0x21,
}
```

---

## Corrected Swap Flow

### ETH -> Token Swap

```python
def swap_exact_in_eth_to_token(
    self,
    token_out: str,
    amount_eth: Decimal,
    slippage_percent: float,
    fee_tier: int
):
    """Correct flow for ETH to token swap."""
    
    commands = []
    inputs = []
    
    # 1. Wrap ETH to WETH
    commands.append(COMMANDS['WRAP_ETH'])
    wrap_input = self.encoder.encode_wrap_eth(
        recipient=self.router_address,
        amount=int(amount_eth * 10**18)
    )
    inputs.append(wrap_input)
    
    # 2. V4 Swap (WETH -> Token)
    # Compute pool key
    weth = "0x4200000000000000000000000000000000000006"
    pool_key = self._get_pool_key(weth, token_out, fee_tier)
    
    # Get quote for slippage
    expected_out = self.quoter.quote_exact_input(...)
    min_out = int(expected_out * (1 - slippage_percent / 100))
    
    # Build swap actions
    actions, params = self.encoder.encode_v4_swap_exact_in(
        pool_key=pool_key,
        amount_in=int(amount_eth * 10**18),
        min_amount_out=min_out,
        recipient=self.account.address,
        zero_for_one=self._is_zero_for_one(weth, token_out)
    )
    
    commands.append(COMMANDS['V4_SWAP'])
    v4_input = encode(['bytes', 'bytes[]'], [actions, params])
    inputs.append(v4_input)
    
    # 3. Sweep any dust
    commands.append(COMMANDS['SWEEP'])
    sweep_input = self.encoder.encode_sweep(
        token=token_out,
        recipient=self.account.address,
        min_amount=1
    )
    inputs.append(sweep_input)
    
    # Execute
    deadline = self.w3.eth.get_block('latest')['timestamp'] + 300
    
    tx = self.router.functions.execute(
        bytes(commands),
        inputs,
        deadline
    ).build_transaction({
        'from': self.account.address,
        'value': int(amount_eth * 10**18),
        'chainId': 8453,
    })
    
    # Estimate gas properly
    try:
        gas = self.router.functions.execute(
            bytes(commands), inputs, deadline
        ).estimate_gas({'from': self.account.address, 'value': tx['value']})
        tx['gas'] = int(gas * 1.2)  # 20% buffer
    except:
        tx['gas'] = 500000  # fallback
    
    tx['gasPrice'] = self.w3.eth.gas_price
    tx['nonce'] = self.w3.eth.get_transaction_count(self.account.address)
    
    # Sign and send
    signed = self.account.sign_transaction(tx)
    tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
    return tx_hash
```

---

## Test Checklist

### Unit Tests (Can Run Without Network)

- [ ] Pool ID calculation with various token pairs
- [ ] Command byte encoding
- [ ] sqrtPriceX96 <-> price conversions
- [ ] Slippage calculations
- [ ] Tick math
- [ ] Error handling for invalid inputs

### Integration Tests (Requires Base Network)

- [ ] Connect to Base and read block number
- [ ] Read COMPUTE pool slot0
- [ ] Calculate COMPUTE price from pool
- [ ] Get quote for ETH->COMPUTE swap
- [ ] Execute small swap (0.001 ETH)
- [ ] Verify transaction succeeded

### Edge Cases

- [ ] Zero amount swaps
- [ ] 100% slippage
- [ ] Tokens with 0 decimals
- [ ] Tokens with 24 decimals
- [ ] Very large amounts
- [ ] Pool doesn't exist
- [ ] Insufficient balance

---

## Gas Estimation Best Practices

```python
def estimate_gas_with_fallback(contract_function, fallback_gas, **tx_params):
    """
    Estimate gas with fallback for complex operations.
    """
    try:
        estimated = contract_function.estimate_gas(tx_params)
        # Add 20% buffer for safety
        return int(estimated * 1.2)
    except ContractLogicError as e:
        # Transaction would revert - don't use fallback
        raise
    except Exception as e:
        # Estimation failed but tx might still work
        # Use fallback with warning
        print(f"Gas estimation failed: {e}, using fallback")
        return fallback_gas

# Usage
tx['gas'] = estimate_gas_with_fallback(
    self.router.functions.execute(commands, inputs, deadline),
    fallback_gas=500000,
    **{'from': account.address, 'value': amount_wei}
)
```

---

## Monitoring & Debugging

Add these helpers for debugging:

```python
def debug_log_swap(self, commands, inputs, tx_hash):
    """Log swap details for debugging."""
    print("=== Swap Debug ===")
    print(f"Commands: {[hex(c) for c in commands]}")
    print(f"Inputs count: {len(inputs)}")
    for i, inp in enumerate(inputs):
        print(f"  Input {i}: {inp[:64]}...")
    print(f"Transaction: {tx_hash}")
    print("==================")

def decode_revert_reason(self, tx_hash):
    """Try to decode why a transaction reverted."""
    try:
        # Replay the transaction to get revert reason
        tx = self.w3.eth.get_transaction(tx_hash)
        self.w3.eth.call(tx, tx['blockNumber'])
    except ContractLogicError as e:
        return str(e)
    except Exception as e:
        return f"Unknown error: {e}"
```

---

## Resources for Testing

### Base Network
- RPC: `https://mainnet.base.org`
- Chain ID: `8453`
- Explorer: `https://basescan.org`

### Uniswap V4 Contracts (Base)
- PoolManager: `0x36089ce6B79A1A30f67F6C7a6c39E28C2D1c4c2d`
- UniversalRouter: `0x6c083a36f731ea994739ef5e8647d18553d41f76`
- Permit2: `0x000000000022D473030F116dDEE9F6B43aC78BA3`
- WETH: `0x4200000000000000000000000000000000000006`

### Documentation
- Universal Router Commands: https://docs.uniswap.org/contracts/universal-router/technical-reference
- V4 Swap Guide: https://docs.uniswap.org/contracts/v4/quickstart/swap
- Actions Library: https://docs.uniswap.org/sdk/v4/reference/enumerations/Actions

---

## Expected Test Output After Fixes

```
$ python -m pytest tests/test_v4_module.py -v

========================= test session starts =========================
platform linux -- Python 3.11.0
plugins: web3-6.15.0

tests/test_v4_module.py::TestPoolManager::test_pool_id_calculation_ordering PASSED
tests/test_v4_module.py::TestPoolManager::test_pool_id_with_different_fees PASSED
tests/test_v4_module.py::TestPoolManager::test_pool_id_with_hooks PASSED
tests/test_v4_module.py::TestPoolManager::test_tick_spacing_mapping PASSED
tests/test_v4_module.py::TestEncoding::test_wrap_eth_encoding PASSED
tests/test_v4_module.py::TestEncoding::test_command_bytes_correctness PASSED
tests/test_v4_module.py::TestQuoter::test_sqrt_price_x96_to_price_basic PASSED
tests/test_v4_module.py::TestQuoter::test_price_roundtrip PASSED
tests/test_v4_module.py::TestQuoter::test_slippage_calculation PASSED
... (all tests passing)

========================== 47 passed in 2.34s ==========================
```

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-15  
**Status:** Ready for implementation
