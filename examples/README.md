# Example Configurations

Example configs for different trading scenarios.

## Available Examples

| File | Description |
|------|-------------|
| `conservative.json` | Low risk, slow trading |
| `standard.json` | Balanced settings |
| `aggressive.json` | High frequency trading |
| `testing.json` | Dry-run mode |
| `swarm.json` | Multi-wallet setup |
| `low-gas.json` | Gas-optimized |

## Usage

```bash
cp examples/standard.json bot_config.json
python bot.py run
```

See [docs/CONFIGURATION.md](../docs/CONFIGURATION.md) for all options.
