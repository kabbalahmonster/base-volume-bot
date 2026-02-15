# 🎯 Example Configurations

This directory contains example configurations for different trading scenarios.

## Available Examples

| File | Description | Use Case |
|------|-------------|----------|
| `conservative.json` | Low risk, slow trading | Beginners, testing |
| `standard.json` | Balanced settings | Regular operation |
| `aggressive.json` | High frequency, high volume | Maximum volume |
| `testing.json` | Dry-run mode | Development |
| `swarm.json` | Multi-wallet setup | Volume multiplication |
| `low-gas.json` | Gas-optimized | Cost-conscious |

## Quick Start

```bash
# Copy an example to your config
cp examples/standard.json bot_config.json

# Run with the config
python bot.py run
```

## Customization

Each config can be customized by editing the values:

```json
{
  "buy_amount_eth": 0.002,        // Change this for different buy sizes
  "buy_interval_minutes": 5,       // Change this for different frequency
  "sell_after_buys": 10            // Change this for different sell triggers
}
```

See [docs/CONFIGURATION.md](../docs/CONFIGURATION.md) for all available options.
