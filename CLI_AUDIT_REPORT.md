# Volume Bot CLI & UX Audit Report
**Date:** 2026-02-14  
**Auditor:** CLI UX Subagent  
**Scope:** bot.py main CLI, swarm_cli.py, README accuracy

---

## 🔴 CRITICAL ISSUES

### 1. Missing/Advertised Commands Not Implemented

| Advertised (README) | Implemented (bot.py) | Status |
|---------------------|---------------------|--------|
| `init` | `setup` | ❌ MISMATCH |
| `status` | **NOT IMPLEMENTED** | ❌ MISSING |
| `wallet-info` | `balance` | ⚠️ RENAMED |

**Impact:** Users following README will get "invalid choice" errors.

### 2. Config Format Mismatch

**bot.py** uses `json`:
```python
with open("bot_config.json", 'w') as f:
    json.dump(config.to_dict(), f, indent=2)
```

**config.py** uses `yaml`:
```python
with open(self.config_path, 'r') as f:
    data = yaml.safe_load(f)
```

**Impact:** Bot creates JSON, but ConfigManager expects YAML. Runtime errors likely.

### 3. Incompatible Encryption Methods

**bot.py - SecureKeyManager:**
- Uses simple SHA256 hash for key derivation
- No salt
- Less secure

**config.py - ConfigManager:**
- Uses PBKDF2 with 480k iterations (OWASP recommended)
- Uses random salt
- More secure

**Impact:** Encrypted files from `setup` cannot be read by `run` if using ConfigManager.

### 4. Withdraw Command Argparse Bug

```python
# Line in main():
withdraw_parser.add_argument("--compute", action="store_true", ...)

# Line in withdraw_command():
withdraw_command(to_address=args.to, amount=args.amount, 
                withdraw_compute=args.compute, dry_run=args.dry_run)
```

The `dest` name is correct, but if user uses the CLI, args.compute works. However, the function signature uses `withdraw_compute` which is correct. Not a bug, but confusing naming.

---

## 🟠 UX ISSUES

### 5. No Pre-flight Dependency Check

Bot crashes immediately with import error if dependencies not installed:
```
ModuleNotFoundError: No module named 'web3'
```

**Expected:** Graceful error message with installation instructions.

### 6. No `--help` Works Without Dependencies

Since imports happen at module level, `bot.py --help` fails before argparse runs.

### 7. Conflicting Command Names Between CLIs

| Command | bot.py | swarm_cli.py |
|---------|--------|--------------|
| `run` | Single bot | Swarm mode |
| `status` | Not implemented | Implemented |
| `balance` | Wallet balance | Not implemented |

Users may be confused about which CLI to use.

### 8. Inconsistent Help Text

**bot.py main()** - Minimal help:
```python
parser = argparse.ArgumentParser(description="$COMPUTE Volume Bot")
```

**swarm_cli.py main()** - Rich help with examples:
```python
parser = argparse.ArgumentParser(
    description="$COMPUTE Swarm Wallet CLI",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""Examples: ..."""
)
```

### 9. No Config Validation

Commands don't validate config before prompting for password. User enters password, then gets "Config not found".

### 10. No Version Command

No `--version` flag to check bot version.

---

## 🟡 MISSING COMMANDS (Should Exist)

### 11. `validate` Command
Should check:
- RPC connectivity
- Wallet balance
- Token approvals
- Gas prices
Without executing trades.

### 12. `config` Command
Should allow:
- `bot.py config show` - Display current config (without private key)
- `bot.py config edit` - Interactive config editing
- `bot.py config reset` - Reset to defaults

### 13. `logs` Command
Should:
- `bot.py logs` - Tail log file
- `bot.py logs --errors` - Show only errors

### 14. `stop` or `pause` Command
No way to gracefully stop a running bot from another terminal.

### 15. `emergency-sell` Command
Immediate sell all positions without waiting for cycle completion.

---

## 📋 COMMAND COMPLETION CHECKLIST

### bot.py Commands

| Command | Implemented | Works E2E | Help Accurate | UX Score |
|---------|-------------|-----------|---------------|----------|
| `setup` | ✅ | ⚠️ (JSON/YAML conflict) | ✅ | 6/10 |
| `run` | ✅ | ⚠️ | ✅ | 7/10 |
| `withdraw` | ✅ | ⚠️ | ✅ | 6/10 |
| `balance` | ✅ | ⚠️ | ✅ | 7/10 |
| `init` (README) | ❌ | N/A | ❌ | 0/10 |
| `status` (README) | ❌ | N/A | ❌ | 0/10 |
| `wallet-info` (README) | ❌ | N/A | ❌ | 0/10 |

### swarm_cli.py Commands

| Command | Implemented | Works E2E | Help Accurate | UX Score |
|---------|-------------|-----------|---------------|----------|
| `create` | ✅ | ⚠️ | ✅ | 8/10 |
| `fund` | ✅ | ⚠️ | ✅ | 7/10 |
| `status` | ✅ | ⚠️ | ✅ | 8/10 |
| `reclaim` | ✅ | ⚠️ | ✅ | 7/10 |
| `rotate` | ✅ | ✅ | ✅ | 7/10 |
| `run` | ✅ | ⚠️ | ✅ | 7/10 |

---

## 🔧 RECOMMENDED FIXES (Priority Order)

### P0 - Critical (Fix Immediately)

1. **Fix README or bot.py** - Align command names:
   - Either add `init` alias to `setup`, or change README to say `setup`
   - Implement `status` command or remove from README
   - Add `wallet-info` alias to `balance`

2. **Fix Config Format** - Standardize on YAML:
   ```python
   # In bot.py setup_command():
   import yaml
   with open("bot_config.yaml", 'w') as f:
       yaml.dump(config.to_dict(), f, default_flow_style=False)
   ```

3. **Fix Import Error on Help** - Move imports inside functions or add guard:
   ```python
   def main():
       try:
           from web3 import Web3
       except ImportError as e:
           print(f"Missing dependency: {e}")
           print("Run: pip install -r requirements.txt")
           sys.exit(1)
   ```

### P1 - High Priority

4. **Add Dependency Check**:
   ```python
   def check_dependencies():
       required = ['web3', 'cryptography', 'rich', 'yaml']
       missing = []
       for pkg in required:
           try:
               __import__(pkg)
           except ImportError:
               missing.append(pkg)
       if missing:
           print(f"Missing packages: {', '.join(missing)}")
           print("Install: pip install -r requirements.txt")
           sys.exit(1)
   ```

5. **Implement `status` Command**:
   ```python
   def status_command():
       # Check if config exists
       # Show config summary (no secrets)
       # Check RPC connectivity
       # Show wallet address and balances
       # Show last log entries
   ```

6. **Add `--version` Flag**:
   ```python
   parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')
   ```

### P2 - Medium Priority

7. **Add `validate` Command** - Pre-flight checks without trading
8. **Improve Error Messages** - Add context and suggestions
9. **Add Config Validation** - Validate before password prompt
10. **Unify Encryption** - Use ConfigManager's PBKDF2 everywhere

### P3 - Nice to Have

11. **Add `config` Subcommand** - For viewing/editing config
12. **Add `logs` Subcommand** - For log viewing
13. **Add `emergency-sell` Command** - Immediate exit
14. **Merge CLIs** - Consider unified `bot.py` with `--swarm` flag

---

## 📝 SPECIFIC CODE FIXES

### Fix 1: README Alignment (bot.py line ~470)
```python
# Add alias support:
if args.command == "setup" or args.command == "init":
    setup_command()
```

### Fix 2: Config Format (bot.py line ~300)
```python
# Change from:
with open("bot_config.json", 'w') as f:
    json.dump(config.to_dict(), f, indent=2)

# To:
import yaml
with open("bot_config.yaml", 'w') as f:
    yaml.dump(config.to_dict(), f, default_flow_style=False)
```

### Fix 3: Lazy Imports (bot.py line ~1)
```python
# Move these inside functions or wrap in try/except:
try:
    from web3 import Web3
    from eth_account import Account
    # ... other crypto imports
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install dependencies: pip install -r requirements.txt")
    sys.exit(1)
```

### Fix 4: Implement status_command (add to bot.py)
```python
def status_command():
    """Check bot status without running"""
    console.print(Panel.fit("[bold cyan]Bot Status Check[/bold cyan]"))
    
    # Check config
    config_path = Path("bot_config.yaml")
    if config_path.exists():
        console.print("[green]✓ Config file exists[/green]")
    else:
        console.print("[red]✗ Config file not found. Run 'setup' first.[/red]")
        return
    
    # Try to load config (without decrypting)
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        console.print("[green]✓ Config file is valid YAML[/green]")
    except Exception as e:
        console.print(f"[red]✗ Config file error: {e}[/red]")
        return
    
    # Show non-sensitive config
    table = Table(title="Configuration", box=box.ROUNDED)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    safe_keys = ['rpc_url', 'buy_amount_eth', 'buy_interval_seconds', 
                 'sell_after_buys', 'dry_run', 'chain_id']
    for key in safe_keys:
        if key in config:
            table.add_row(key, str(config[key]))
    
    console.print(table)
    console.print("\n[dim]Use 'run' to start the bot with full functionality[/dim]")
```

---

## 📊 SUMMARY

**Commands Working:** 4/7 (57%)  
**README Accuracy:** 3/7 (43%)  
**Overall UX Score:** 6/10

### Critical Path to Working CLI:
1. Fix README ↔ Code alignment (15 min)
2. Fix config format consistency (15 min)
3. Add dependency check (10 min)
4. Implement missing `status` command (30 min)

**Total estimated fix time: ~1.5 hours**

### Testing Checklist After Fixes:
- [ ] `python bot.py --help` works without dependencies
- [ ] `python bot.py setup` creates valid YAML config
- [ ] `python bot.py status` shows config without password
- [ ] `python bot.py balance` shows wallet info
- [ ] `python bot.py run --dry-run` simulates trades
- [ ] `python bot.py withdraw` works end-to-end
- [ ] All README examples execute correctly
