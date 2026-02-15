# Configuration Guide

Complete reference for all configuration options.

## Configuration File

The bot uses `bot_config.json` for settings. Create it via:
- `python bot.py setup` (interactive)
- Manual creation

## Full Configuration Reference

```json
{
  "rpc_url": "https://base.drpc.org",
  "chain_id": 8453,
  "compute_token": "0x696381f39F17cAD67032f5f52A4924ce84e51BA3",
  "weth_address": "0x4200000000000000000000000000000000000006",
  "router_address": "0x2626664c2603336E57B271c5C0b26F421741e481",
  "quoter_address": "0x3d4e44Eb1374240CE5F1B871ab261CD16335CB76",
  "factory_address": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD",
  "buy_amount_eth": 0.002,
  "buy_interval_seconds": 300,
  "sell_after_buys": 10,
  "max_gas_price_gwei": 5.0,
  "slippage_percent": 2.0,
  "gas_limit_buffer": 1.2,
  "dry_run": false,
  "log_level": "INFO",
  "log_file": "./bot.log",
  "max_retries": 3,
  "retry_delay_seconds": 5,
  "pool_fee": 3000,
  "oneinch_api_key": null,
  "zerox_api_key": null
}
```

## Trading Settings

### `buy_amount_eth`
Amount of ETH to spend per buy.
- Type: float
- Default: 0.002
- Example: 0.002 = $5-10 worth at current prices

### `buy_interval_seconds`
Time between buys in seconds.
- Type: int
- Default: 300 (5 minutes)
- Minimum: 60 (1 minute)

### `sell_after_buys`
Number of buys before selling accumulated tokens.
- Type: int
- Default: 10
- Set to 0 to disable auto-selling

### `slippage_percent`
Maximum allowed slippage.
- Type: float
- Default: 2.0
- Range: 0.1 - 50.0
- Higher = more likely to succeed but worse price

## Gas Settings

### `max_gas_price_gwei`
Maximum gas price in gwei.
- Type: float
- Default: 5.0
- Transactions will wait if gas is higher

### `gas_limit_buffer`
Multiplier for gas estimation.
- Type: float
- Default: 1.2 (20% buffer)
- Prevents out-of-gas failures

## Network Settings

### `rpc_url`
Base network RPC endpoint.
- Type: string
- Default: "https://base.drpc.org"
- Options: drpc, base.org, llamaRPC

### `chain_id`
Network chain ID.
- Type: int
- Default: 8453 (Base)
- Do not change unless porting to other chain

## API Keys

### `zerox_api_key`
0x aggregator API key.
- Type: string or null
- Get from: https://0x.org
- Enables: Best prices, V4 support

### `oneinch_api_key`
1inch aggregator API key.
- Type: string or null
- Get from: https://portal.1inch.dev
- Alternative to 0x

## Operation Settings

### `dry_run`
Simulate without sending transactions.
- Type: boolean
- Default: false
- Useful for testing

### `log_level`
Logging verbosity.
- Type: string
- Default: "INFO"
- Options: DEBUG, INFO, WARNING, ERROR

### `max_retries`
Number of retry attempts on failure.
- Type: int
- Default: 3
- Applies to network errors

## Security Settings

### File Permissions
The bot automatically sets:
- `.bot_wallet.enc`: 0o600 (owner read/write only)
- `bot_config.json`: 0o644 (owner read/write, group read)

### Encryption
- Algorithm: PBKDF2-HMAC-SHA256
- Iterations: 600,000
- Cipher: Fernet (AES-128-CBC)

## Environment Variables

Instead of config file, you can use environment:

```bash
export ZEROX_API_KEY="your_key"
export ONEINCH_API_KEY="your_key"
export BOT_LOG_LEVEL="DEBUG"
```

## Token-Specific Configs

Create separate configs for different tokens:

```bash
# BNKR config
cp bot_config.json bnk_config.json
# Edit bnk_config.json

# Run with specific config
python bot.py --config bnk_config.json run
```

## Validation

The bot validates configuration on startup:
- Checks RPC connectivity
- Validates token addresses
- Verifies wallet has ETH
- Warns about missing API keys

## Troubleshooting Config

### Reset to defaults:
```bash
rm bot_config.json
python bot.py setup
```

### View current config:
```bash
cat bot_config.json | python -m json.tool
```

### Test RPC:
```bash
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  https://base.drpc.org
```
