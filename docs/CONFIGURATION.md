# ⚙️ Configuration Guide

Complete configuration reference for the $COMPUTE Volume Bot.

---

## Table of Contents

1. [Configuration Files](#configuration-files)
2. [Basic Settings](#basic-settings)
3. [Network Configuration](#network-configuration)
4. [Trading Parameters](#trading-parameters)
5. [Gas Settings](#gas-settings)
6. [Security Settings](#security-settings)
7. [Advanced Settings](#advanced-settings)
8. [Environment Variables](#environment-variables)
9. [Configuration Examples](#configuration-examples)

---

## Configuration Files

### Main Configuration Files

| File | Purpose | Created By |
|------|---------|------------|
| `bot_config.json` | Main bot settings | `bot.py setup` |
| `.wallet.enc` | Encrypted private key | `bot.py setup` |
| `volume_bot.log` | Activity logs | Runtime |
| `example_config.yaml` | Example YAML config | Package |

---

## Basic Settings

### Core Trading Parameters

```json
{
  "buy_amount_eth": 0.002,
  "buy_interval_minutes": 5,
  "sell_after_buys": 10
}
```

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `buy_amount_eth` | float | 0.002 | ETH amount per buy transaction |
| `buy_interval_minutes` | int | 5 | Minutes between buy attempts |
| `sell_after_buys` | int | 10 | Number of buys before selling all |

---

## Configuration Examples

### Conservative (Safe)

```json
{
  "buy_amount_eth": 0.001,
  "buy_interval_minutes": 15,
  "sell_after_buys": 20,
  "slippage_percent": 1.0,
  "max_gas_gwei": 0.3
}
```

### Standard (Balanced)

```json
{
  "buy_amount_eth": 0.002,
  "buy_interval_minutes": 5,
  "sell_after_buys": 10,
  "slippage_percent": 2.0,
  "max_gas_gwei": 0.5
}
```

### Aggressive (High Volume)

```json
{
  "buy_amount_eth": 0.01,
  "buy_interval_minutes": 2,
  "sell_after_buys": 5,
  "slippage_percent": 3.0,
  "max_gas_gwei": 1.0
}
```

---

See [SETUP.md](SETUP.md) for installation guide.
