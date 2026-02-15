# Uniswap V4 Trading Module

A reusable, token-agnostic trading module for Uniswap V4 on Base.

## Overview

This module provides a clean, simple API for interacting with Uniswap V4 pools, handling all the complexity of V4's new architecture internally.

### Key Features

- 🔧 **Token-agnostic**: Works with any V4 pool on Base
- 🔄 **Reusable**: Can be used by multiple bots/trading strategies
- 🧠 **Simple API**: Just `buy()` and `sell()` - complexity handled internally
- 📊 **Price quoting**: Get current prices and quotes
- 🛡️ **Slippage protection**: Built-in slippage controls
- 🔐 **Permit2 integration**: Modern approval mechanism

## Architecture

```
v4_trading/
├── __init__.py         # Main V4Trader API
├── pool_manager.py     # PoolManager interactions
├── universal_router.py # UniversalRouter swap execution
├── encoding.py         # V4 command encoding
└── quoter.py           # Price quoting
```

### V4 Contracts (Base)

| Contract | Address |
|----------|---------|
| PoolManager | `0x36089ce6B79A1A30f67F6C7a6c39E28C2D1c4c2d` |
| UniversalRouter | `0x6c083a36f731ea994739ef5e8647d18553d41f76` |
| WETH | `0x4200000000000000000000000000000000000006` |
| Permit2 | `0x000000000022D473030F116dDEE9F6B43aC78BA3` |

## Installation

```bash
# Copy the v4_trading folder to your project
cp -r v4_trading /path/to/your/project/

# Or install as package
cd v4_trading
pip install -e .
```

### Requirements

```
web3>=6.0.0
eth-account>=0.8.0
eth-abi>=4.0.0
```

## Quick Start

### Basic Usage

```python
from web3 import Web3
from eth_account import Account
from v4_trading import V4Trader

# Setup
w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))
account = Account.from_key('your_private_key')

# Initialize trader
trader = V4Trader(w3, account)

# Buy tokens with ETH
success, result = trader.buy(
    token_address='0x...',  # Token to buy
    amount_eth=0.1,          # ETH to spend
    slippage_percent=2.0     # 2% slippage
)

if success:
    print(f"Bought! TX: {result}")
else:
    print(f"Failed: {result}")

# Sell tokens for ETH
success, result = trader.sell(
    token_address='0x...',  # Token to sell
    amount_tokens=100,       # Token amount
    slippage_percent=2.0
)
```

### Get Price

```python
# Get current price
success, price = trader.get_price(token_address='0x...')

if success:
    print(f"Price: {price} ETH per token")
```

### Get Pool Info

```python
# Get pool information
pool_info = trader.get_pool_info(
    token0='0x...',  # WETH
    token1='0x...',  # Token
    fee_tier=3000    # 0.3%
)

print(f"Pool ID: {pool_info['pool_id']}")
print(f"sqrtPriceX96: {pool_info['sqrtPriceX96']}")
print(f"Current tick: {pool_info['tick']}")
```

## Advanced Usage

### Custom Fee Tier

```python
# Use different fee tier (default is 3000 = 0.3%)
# Available: 100 (0.01%), 500 (0.05%), 3000 (0.3%), 10000 (1%)

success, result = trader.buy(
    token_address='0x...',
    amount_eth=0.1,
    fee_tier=500  # 0.05% fee
)
```

### Direct Pool Manager Access

```python
from v4_trading import V4PoolManager

pool_manager = V4PoolManager(w3, POOL_MANAGER_ADDRESS)

# Compute pool ID
pool_id = pool_manager.get_pool_id(
    token0='0x...',
    token1='0x...',
    fee=3000
)

# Get pool state
slot0 = pool_manager.get_slot0(pool_id)
print(f"Price: {slot0['sqrtPriceX96']}")
print(f"Tick: {slot0['tick']}")
```

### Direct Router Access

```python
from v4_trading import V4UniversalRouter

router = V4UniversalRouter(w3, account, UNIVERSAL_ROUTER_ADDRESS)

# Execute custom swap
success, tx_hash = router.swap_exact_in(
    token_in=WETH,
    token_out='0x...',
    amount_in_eth=0.1,
    slippage_percent=2.0,
    fee_tier=3000
)
```

### Price Quoting

```python
from v4_trading import V4Quoter

quoter = V4Quoter(w3, pool_manager)

# Quote swap
success, amount_out = quoter.quote_exact_input(
    pool_id=pool_id,
    amount_in=1000000,  # 1 USDC (6 decimals)
    token_in_decimals=6,
    token_out_decimals=18,
    zero_for_one=True
)

# Calculate min output with slippage
min_output = quoter.calculate_min_output(amount_out, slippage_percent=2.0)
```

## API Reference

### V4Trader

Main trading interface.

#### `__init__(w3, account, **kwargs)`

Initialize trader.

**Parameters:**
- `w3` (Web3): Web3 instance
- `account` (Account): Account for signing
- `pool_manager_address` (str, optional): Custom PoolManager address
- `universal_router_address` (str, optional): Custom UniversalRouter address
- `default_slippage` (float, optional): Default slippage % (default: 2.0)
- `default_fee_tier` (int, optional): Default fee tier (default: 3000)

#### `buy(token_address, amount_eth, **kwargs)`

Buy tokens with ETH.

**Parameters:**
- `token_address` (str): Token to buy
- `amount_eth` (float/Decimal): ETH amount
- `slippage_percent` (float, optional): Max slippage
- `fee_tier` (int, optional): Pool fee tier

**Returns:** `(success: bool, tx_hash_or_error: str)`

#### `sell(token_address, amount_tokens, **kwargs)`

Sell tokens for ETH.

**Parameters:**
- `token_address` (str): Token to sell
- `amount_tokens` (float/Decimal): Token amount
- `slippage_percent` (float, optional): Max slippage
- `fee_tier` (int, optional): Pool fee tier

**Returns:** `(success: bool, tx_hash_or_error: str)`

#### `get_price(token_address, **kwargs)`

Get token price in ETH.

**Returns:** `(success: bool, price_or_error: Decimal/str)`

#### `get_pool_info(token0, token1, **kwargs)`

Get pool information.

**Returns:** `dict` with pool_id, sqrtPriceX96, tick, liquidity

### V4PoolManager

Low-level PoolManager interactions.

#### `get_pool_id(token0, token1, fee, **kwargs)`

Compute pool ID from tokens and fee.

**Returns:** `str` (bytes32 hex)

#### `get_slot0(pool_id)`

Get current pool state.

**Returns:** `dict` with sqrtPriceX96, tick, protocolFee, swapFee

#### `get_liquidity(pool_id)`

Get total pool liquidity.

**Returns:** `int` or `None`

#### `pool_exists(token0, token1, fee)`

Check if pool exists.

**Returns:** `bool`

### V4UniversalRouter

Swap execution through Universal Router.

#### `swap_exact_in(token_in, token_out, amount_in_eth, slippage_percent, fee_tier, **kwargs)`

Execute exact-input swap (ETH → Token).

**Returns:** `(success: bool, tx_hash_or_error: str)`

#### `swap_exact_out(token_in, token_out, amount_in_tokens, token_decimals, slippage_percent, fee_tier, **kwargs)`

Execute exact-output swap (Token → ETH).

**Returns:** `(success: bool, tx_hash_or_error: str)`

### V4Quoter

Price calculations and quoting.

#### `sqrt_price_x96_to_price(sqrt_price_x96, token0_decimals, token1_decimals)`

Convert sqrtPriceX96 to human-readable price.

**Returns:** `Decimal`

#### `quote_exact_input(pool_id, amount_in, token_in_decimals, token_out_decimals, **kwargs)`

Quote expected output for input amount.

**Returns:** `(success: bool, amount_out_or_error: int/str)`

#### `calculate_min_output(expected_output, slippage_percent)`

Calculate minimum output with slippage.

**Returns:** `int`

## Fee Tiers

| Fee | Description | Use Case |
|-----|-------------|----------|
| 100 | 0.01% | Stable pairs |
| 500 | 0.05% | Major pairs |
| 3000 | 0.3% | Most pairs (default) |
| 10000 | 1% | Exotic pairs |

## COMPUTE Pool Reference

For reference, the COMPUTE pool on Base:

```python
COMPUTE_POOL_ID = "0x40332cd73d9c79b34aa477cbd7e6962387dcfda042a12c72ad94bc58262023bf"

# Or compute it:
pool_id = pool_manager.get_pool_id(
    token0=WETH,  # 0x4200000000000000000000000000000000000006
    token1=COMPUTE,  # COMPUTE token address
    fee=3000
)
```

## Comparison with 0x Aggregator

This module is designed to be a direct V4 alternative to the 0x aggregator approach:

| Feature | V4 Direct | 0x Aggregator |
|---------|-----------|---------------|
| Gas Cost | Lower | Higher (aggregation overhead) |
| Price | Single source | Best across DEXs |
| Complexity | Higher (V4 specific) | Lower (API handles it) |
| Reliability | High (direct) | Depends on API |
| Speed | Fast | API latency |

Use this module when:
- You know the V4 pool has good liquidity
- You want lower gas costs
- You want direct execution without API dependencies

Use 0x when:
- You want the best price across all DEXs
- You're trading exotic tokens
- Simplicity is preferred over gas optimization

## Error Handling

All methods return `(success: bool, result: str)` tuples:

```python
success, result = trader.buy(token, 0.1)

if not success:
    # result contains error message
    if "insufficient funds" in result:
        print("Not enough ETH!")
    elif "slippage" in result:
        print("Price moved too much!")
    else:
        print(f"Error: {result}")
```

Common errors:
- `Pool not found`: The token/fee combination doesn't have a V4 pool
- `insufficient funds`: Not enough ETH or tokens
- `slippage exceeded`: Price moved beyond your slippage tolerance
- `approval failed`: Token approval transaction failed

## Testing

```bash
# Run tests (when implemented)
pytest tests/test_v4_trading.py

# Test specific components
pytest tests/test_pool_manager.py
pytest tests/test_universal_router.py
```

## Contributing

This module is part of the volume_bot project. To contribute:

1. Create a feature branch: `git checkout -b feature/v4-improvement`
2. Make your changes
3. Add tests
4. Submit a PR

## License

MIT - See LICENSE file for details

## Resources

- [Uniswap V4 Docs](https://docs.uniswap.org/contracts/v4/overview)
- [V4 Whitepaper](https://uniswap.org/whitepaper-v4.pdf)
- [Base Chain Docs](https://docs.base.org/)
- [PoolManager Source](https://github.com/Uniswap/v4-core)
- [UniversalRouter Source](https://github.com/Uniswap/universal-router)

## Support

For issues or questions:
- Open an issue in the repository
- Check the Uniswap Discord
- Review V4 documentation
