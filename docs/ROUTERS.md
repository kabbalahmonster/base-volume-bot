# 🌐 DEX Router Guide

Complete guide to the DEX routers supported by the $COMPUTE Volume Bot.

---

## Table of Contents

1. [Router Overview](#router-overview)
2. [Uniswap V3](#uniswap-v3)
3. [1inch Aggregator](#1inch-aggregator)
4. [0x Aggregator](#0x-aggregator)
5. [Uniswap V4](#uniswap-v4)
6. [Router Comparison](#router-comparison)
7. [Router Selection](#router-selection)
8. [Troubleshooting](#troubleshooting)

---

## Router Overview

### What is a DEX Router?

A DEX (Decentralized Exchange) router is a smart contract that facilitates token swaps on the blockchain. The bot uses routers to:

- Execute buy transactions (ETH → COMPUTE)
- Execute sell transactions (COMPUTE → ETH)
- Find optimal pricing
- Handle transaction routing

### Supported Routers

| Router | Type | Module File |
|--------|------|-------------|
| **Uniswap V3** | AMM | `dex_router.py` |
| **1inch** | Aggregator | `oneinch_router.py` |
| **0x** | Aggregator | `zerox_router.py` |
| **Uniswap V4** | AMM | `v4_router.py` |

---

## Uniswap V3

### Overview

Uniswap V3 is the most popular decentralized exchange on Base. It uses concentrated liquidity to provide efficient trading.

```python
# Module: dex_router.py
# Class: MultiDEXRouter
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Concentrated Liquidity** | Liquidity providers concentrate funds in specific price ranges |
| **Multiple Fee Tiers** | 0.05%, 0.3%, and 1% pools available |
| **Direct Swaps** | No intermediate tokens needed |
| **Mature Ecosystem** | Well-tested and audited |

### Configuration

```json
{
  "dex_router": "uniswap_v3",
  "uniswap_v3": {
    "router_address": "0x2626664c2603336E57B271c5C0b26F421741e481",
    "quoter_address": "0x3d4e44Eb1374240CE5F1B871ab261CD16335CB76",
    "factory_address": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD",
    "default_fee_tier": 3000
  }
}
```

### Fee Tiers

| Tier | Fee | Best For |
|------|-----|----------|
| 500 | 0.05% | Stable pairs, high volume |
| 3000 | 0.3% | Standard pairs (default) |
| 10000 | 1% | Exotic pairs, low liquidity |

### Gas Costs

| Operation | Gas Estimate | Cost @ 0.1 Gwei |
|-----------|--------------|-----------------|
| Buy | ~150,000 | ~$0.0005 |
| Sell | ~200,000 | ~$0.0007 |

### When to Use

✅ **Best for:**
- Standard trading
- Reliable execution
- Low gas costs
- Well-established liquidity

❌ **Not ideal for:**
- Best price across all DEXs
- MEV protection
- Complex routing

---

## 1inch Aggregator

### Overview

1inch is a DEX aggregator that finds the best prices across multiple exchanges by splitting orders and routing through optimal paths.

```python
# Module: oneinch_router.py
# Class: OneInchAggregator
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Multi-DEX Routing** | Splits orders across multiple DEXs |
| **Path Optimization** | Finds cheapest route automatically |
| **Partial Fills** | Can execute partial orders |
| **Gas Optimization** | Minimizes total gas cost |

### Configuration

```json
{
  "dex_router": "1inch",
  "oneinch": {
    "api_base_url": "https://api.1inch.dev",
    "version": "v5.2",
    "protocols": ["UNISWAP_V3", "SUSHISWAP", "CURVE"],
    "max_slippage": 2.0
  }
}
```

### Supported Protocols

| Protocol | Type |
|----------|------|
| Uniswap V3 | AMM |
| Uniswap V2 | AMM |
| SushiSwap | AMM |
| Curve | Stable AMM |
| BaseSwap | AMM |

### Gas Costs

| Operation | Gas Estimate | Cost @ 0.1 Gwei |
|-----------|--------------|-----------------|
| Buy | ~180,000 | ~$0.0006 |
| Sell | ~220,000 | ~$0.0008 |

### When to Use

✅ **Best for:**
- Getting best possible price
- Large orders
- Price-sensitive trading
- Multiple liquidity sources

❌ **Not ideal for:**
- Gas-constrained environments
- Simple, quick trades
- When API is unavailable

---

## 0x Aggregator

### Overview

0x is a professional-grade DEX aggregator with a focus on MEV protection and institutional trading.

```python
# Module: zerox_router.py
# Class: ZeroXAggregator
```

### Key Features

| Feature | Description |
|---------|-------------|
| **MEV Protection** | Protects against sandwich attacks |
| **Professional API** | Institutional-grade pricing |
| **Slippage Protection** | Advanced slippage controls |
| **Gas Refunds** | Potential gas token refunds |

### Configuration

```json
{
  "dex_router": "0x",
  "zerox": {
    "api_base_url": "https://api.0x.org",
    "api_key": "optional-api-key",
    "enable_mev_protection": true,
    "taker_address": "your-wallet-address"
  }
}
```

### MEV Protection

```
Without MEV Protection:
  User Swap → MEV Bot Frontruns → User Gets Worse Price

With MEV Protection (0x):
  User Swap → Private Mempool → Protected Execution → Fair Price
```

### Gas Costs

| Operation | Gas Estimate | Cost @ 0.1 Gwei |
|-----------|--------------|-----------------|
| Buy | ~160,000 | ~$0.0005 |
| Sell | ~210,000 | ~$0.0007 |

### When to Use

✅ **Best for:**
- MEV protection
- Large orders
- Institutional trading
- Security-conscious users

❌ **Not ideal for:**
- When MEV protection not needed
- API rate limits
- Simple transactions

---

## Uniswap V4

### Overview

Uniswap V4 is the next generation of Uniswap with hooks, singleton architecture, and improved gas efficiency.

```python
# Module: v4_router.py
# Class: V4DirectRouter
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Hooks** | Customizable pool behavior |
| **Singleton Architecture** | All pools in one contract |
| **Gas Efficiency** | ~10-20% lower gas costs |
| **Flash Accounting** | Optimized for multi-hop swaps |

### Configuration

```json
{
  "dex_router": "uniswap_v4",
  "uniswap_v4": {
    "pool_manager": "0x...",
    "swap_router": "0x...",
    "quoter": "0x...",
    "hook_enabled": false
  }
}
```

### Gas Costs

| Operation | Gas Estimate | Cost @ 0.1 Gwei | vs V3 |
|-----------|--------------|-----------------|-------|
| Buy | ~130,000 | ~$0.0004 | -13% |
| Sell | ~170,000 | ~$0.0006 | -15% |

### When to Use

✅ **Best for:**
- Gas-sensitive operations
- Advanced features
- Future-proofing
- High-frequency trading

❌ **Not ideal for:**
- Conservative users
- When V4 liquidity is low
- Simple use cases

---

## Router Comparison

### Feature Comparison

| Feature | Uniswap V3 | 1inch | 0x | Uniswap V4 |
|---------|-----------|-------|-----|-----------|
| **Price Optimization** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **Gas Efficiency** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **MEV Protection** | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| **Reliability** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Speed** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

### Use Case Recommendations

| Use Case | Recommended Router | Why |
|----------|-------------------|-----|
| Standard Trading | Uniswap V3 | Reliable, fast, proven |
| Best Price | 1inch | Aggregates all sources |
| Large Orders | 0x | MEV protection |
| Gas Savings | Uniswap V4 | Lowest gas costs |
| Beginners | Uniswap V3 | Simplest interface |
| High Frequency | Uniswap V4 | Fastest + cheapest |

---

## Router Selection

### Automatic Selection

The bot can automatically select the best router:

```json
{
  "dex_router": "auto",
  "router_priority": ["1inch", "uniswap_v3", "0x", "uniswap_v4"]
}
```

### Selection Criteria

The auto-router considers:
1. **Price** - Best output amount
2. **Gas Cost** - Total transaction cost
3. **Success Rate** - Historical reliability
4. **Speed** - Expected confirmation time

### Manual Selection

Force a specific router:

```json
{
  "dex_router": "uniswap_v3"
}
```

### Per-Transaction Selection

Override router for single transaction (via CLI):

```bash
# Force specific router
python bot.py run --router 1inch

# Force specific router for swarm
python swarm_cli.py run --router 0x
```

---

## Router Error Handling

### Common Router Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "INSUFFICIENT_LIQUIDITY" | Pool has low liquidity | Try different router or increase slippage |
| "EXCESSIVE_SLIPPAGE" | Price moved too much | Increase slippage tolerance |
| "ROUTER_QUOTE_FAILED" | API error | Retry or switch router |
| "GAS_ESTIMATION_FAILED" | Complex transaction | Try simpler router |

### Fallback Mechanism

The bot automatically falls back to other routers:

```python
# Primary: 1inch
# Fallback 1: Uniswap V3
# Fallback 2: 0x
# Fallback 3: Uniswap V4
```

### Configuring Fallback

```json
{
  "router_fallback": true,
  "fallback_order": ["uniswap_v3", "0x", "uniswap_v4"]
}
```

---

## Troubleshooting

### Router-Specific Issues

#### Uniswap V3

**Issue:** "Pool does not exist"  
**Solution:** The token pair doesn't have a pool on Uniswap V3. Try 1inch or 0x.

**Issue:** "TickMath: invalid tick"  
**Solution:** Extreme price movement. Increase slippage or wait for stability.

#### 1inch

**Issue:** "API rate limit exceeded"  
**Solution:** Wait a moment and retry, or use different router.

**Issue:** "No routes found"  
**Solution:** Insufficient liquidity across all DEXs. Try Uniswap V3 directly.

#### 0x

**Issue:** "Quote expired"  
**Solution:** Quote valid for short time. Retry transaction.

**Issue:** "Insufficient allowance"  
**Solution:** Token approval needed. Bot handles this automatically.

#### Uniswap V4

**Issue:** "Pool not initialized"  
**Solution:** V4 is newer. Try Uniswap V3 for better liquidity.

**Issue:** "Hook validation failed"  
**Solution:** Some hooks may block trading. Try different router.

---

## Advanced Configuration

### Custom Router Integration

To add a custom router:

1. Create router module:
```python
# custom_router.py
class CustomRouter:
    def get_quote(self, amount_in, token_in, token_out):
        # Implementation
        pass
    
    def execute_swap(self, quote, wallet):
        # Implementation
        pass
```

2. Register in config:
```json
{
  "custom_routers": {
    "my_router": {
      "module": "custom_router.py",
      "class": "CustomRouter"
    }
  }
}
```

### Router Analytics

Track router performance:

```bash
# View router statistics in logs
grep "ROUTER_STATS" volume_bot.log

# Example output:
# ROUTER_STATS: uniswap_v3 - 45 trades, avg_gas: 150k, success_rate: 98%
# ROUTER_STATS: 1inch - 23 trades, avg_gas: 180k, success_rate: 95%
```

---

## See Also

- [CONFIGURATION.md](CONFIGURATION.md) - General configuration
- [SETUP.md](SETUP.md) - Installation guide
- [API_REFERENCE.md](API_REFERENCE.md) - Technical API docs
