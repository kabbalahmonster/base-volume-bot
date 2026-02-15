# 🌐 DEX Router Guide

Guide to the DEX routers supported by the Volume Bot.

---

## Supported Routers

| Router | Type | Best For | Gas Cost |
|--------|------|----------|----------|
| **Uniswap V3** | AMM | Standard trades | Medium |
| **1inch** | Aggregator | Best price routing | Higher |
| **0x** | Aggregator | MEV protection | Medium |
| **Uniswap V4** | AMM | Advanced features | Lower |

---

## Uniswap V3

The most popular DEX on Base. Uses concentrated liquidity for efficient trading.

### Configuration

```json
{
  "dex_router": "uniswap_v3",
  "uniswap_v3": {
    "router_address": "0x2626664c2603336E57B271c5C0b26F421741e481",
    "default_fee_tier": 3000
  }
}
```

### Fee Tiers

| Tier | Fee | Best For |
|------|-----|----------|
| 500 | 0.05% | Stable pairs |
| 3000 | 0.3% | Standard pairs (default) |
| 10000 | 1% | Exotic pairs |

---

## 1inch Aggregator

Finds best prices across multiple DEXs.

### Configuration

```json
{
  "dex_router": "1inch",
  "router_priority": ["1inch", "uniswap_v3", "0x"]
}
```

---

## 0x Aggregator

Professional-grade with MEV protection.

### Configuration

```json
{
  "dex_router": "0x",
  "zerox": {
    "enable_mev_protection": true
  }
}
```

---

## Router Selection

### Automatic Selection

```json
{
  "dex_router": "auto",
  "router_priority": ["1inch", "uniswap_v3", "0x"]
}
```

### Manual Selection

```json
{
  "dex_router": "uniswap_v3"
}
```

---

See [CONFIGURATION.md](CONFIGURATION.md) for more options.
