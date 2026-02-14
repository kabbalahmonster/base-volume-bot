# Wallet Security Hardening Recommendations

**Document Version:** 1.0  
**Date:** 2026-02-14  
**Classification:** Internal Use

---

## Priority 1: Critical Hardening (Implement Immediately)

### 1.1 Fix Key Derivation in bot.py

**Current Vulnerable Code:**
```python
def _derive_key(self, password: str) -> bytes:
    key = hashlib.sha256(password.encode()).digest()
    return base64.urlsafe_b64encode(key)
```

**Hardened Implementation:**
```python
import os
import base64
import json
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

class SecureKeyManager:
    """Manages encrypted private keys with PBKDF2-HMAC-SHA256"""
    
    # OWASP 2023 recommendation: 600,000 iterations minimum
    KDF_ITERATIONS = 600000
    SALT_LENGTH = 32  # Increased from 16 for post-quantum safety margin
    
    def __init__(self, key_file: str = ".wallet.enc"):
        self.key_file = Path(key_file)
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key using PBKDF2-HMAC-SHA256"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.KDF_ITERATIONS,
        )
        key = kdf.derive(password.encode('utf-8'))
        return base64.urlsafe_b64encode(key)
    
    def encrypt_and_save(self, private_key: str, password: str) -> bool:
        """Encrypt and save private key with salt"""
        try:
            # Generate cryptographically secure random salt
            salt = os.urandom(self.SALT_LENGTH)
            
            # Derive key from password
            key = self._derive_key(password, salt)
            f = Fernet(key)
            
            # Encrypt private key
            encrypted = f.encrypt(private_key.encode('utf-8'))
            
            # Store with metadata for future KDF upgrades
            data = {
                "version": 2,  # Version for future migrations
                "encrypted": base64.b64encode(encrypted).decode(),
                "salt": base64.b64encode(salt).decode(),
                "kdf": "pbkdf2-sha256",
                "iterations": self.KDF_ITERATIONS,
                "created": datetime.now().isoformat(),
            }
            
            # Atomic write (write to temp, then rename)
            temp_file = self.key_file.with_suffix('.tmp')
            with open(temp_file, 'w') as file:
                json.dump(data, file)
            
            # Set restrictive permissions before rename
            os.chmod(temp_file, 0o600)
            temp_file.rename(self.key_file)
            
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to save wallet: {e}[/red]")
            return False
    
    def load_and_decrypt(self, password: str) -> Optional[str]:
        """Load and decrypt private key"""
        try:
            if not self.key_file.exists():
                return None
            
            with open(self.key_file, 'r') as file:
                data = json.load(file)
            
            # Handle version migration
            version = data.get("version", 1)
            
            if version == 1:
                # Legacy format - warning about weak encryption
                console.print("[yellow]⚠️  WARNING: Using legacy encryption. Run 'upgrade-wallet' to strengthen.[/yellow]")
                key = hashlib.sha256(password.encode()).digest()
                key = base64.urlsafe_b64encode(key)
                salt = None
            else:
                # Current format
                salt = base64.b64decode(data["salt"])
                key = self._derive_key(password, salt)
            
            f = Fernet(key)
            encrypted_bytes = base64.b64decode(data["encrypted"])
            decrypted = f.decrypt(encrypted_bytes)
            
            return decrypted.decode('utf-8')
            
        except Exception as e:
            console.print(f"[red]Failed to decrypt wallet: {e}[/red]")
            return None
```

---

### 1.2 Secure Memory Management

**Problem:** Private keys remain in memory after use.

**Solution - SecureWallet Class:**
```python
import ctypes
import gc
from typing import Optional
from eth_account import Account

class SecureWallet:
    """Wallet with secure memory handling"""
    
    def __init__(self, config: Config, password: Optional[str] = None):
        self.config = config
        self._web3 = Web3(Web3.HTTPProvider(config.rpc_url))
        
        # Validate connection
        if not self._web3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC: {config.rpc_url}")
        
        # Initialize account - key stored temporarily
        if not config.encrypted_private_key:
            raise ValueError("No private key provided")
        
        # Store key in mutable bytearray for secure deletion
        key_bytes = bytearray(config.encrypted_private_key, 'utf-8')
        self._account = Account.from_key(bytes(key_bytes))
        self.address = self._account.address
        
        # Clear key from memory immediately after use
        self._secure_clear(key_bytes)
        
        # Remove reference to private key in account object
        self._account = type('obj', (object,), {
            'address': self._account.address,
            'sign_transaction': self._account.sign_transaction,
        })()
        
        logger.info(f"Wallet initialized: {self.address}")
    
    def _secure_clear(self, data: bytearray) -> None:
        """Securely clear data from memory"""
        for i in range(len(data)):
            data[i] = 0
        
        # Force garbage collection
        gc.collect()
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        if hasattr(self, '_account'):
            self._account = None
```

---

### 1.3 Rate Limiting for Password Attempts

```python
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class FailedAttempt:
    timestamp: float
    count: int

class PasswordRateLimiter:
    """Rate limiter for password attempts"""
    
    MAX_ATTEMPTS = 5
    LOCKOUT_DURATION = 3600  # 1 hour
    ATTEMPT_WINDOW = 300     # 5 minutes
    
    def __init__(self):
        self._attempts: Dict[str, List[float]] = defaultdict(list)
        self._lockouts: Dict[str, float] = {}
    
    def check_allowed(self, key: str) -> tuple[bool, Optional[str]]:
        """Check if operation is allowed for key"""
        now = time.time()
        
        # Check if currently locked out
        if key in self._lockouts:
            if now < self._lockouts[key]:
                remaining = int(self._lockouts[key] - now)
                return False, f"Locked out. Try again in {remaining} seconds."
            else:
                del self._lockouts[key]
        
        # Clean old attempts
        self._attempts[key] = [
            t for t in self._attempts[key] 
            if now - t < self.ATTEMPT_WINDOW
        ]
        
        # Check attempt count
        if len(self._attempts[key]) >= self.MAX_ATTEMPTS:
            self._lockouts[key] = now + self.LOCKOUT_DURATION
            return False, f"Too many attempts. Locked for {self.LOCKOUT_DURATION} seconds."
        
        return True, None
    
    def record_attempt(self, key: str, success: bool):
        """Record an authentication attempt"""
        if success:
            # Clear attempts on success
            self._attempts[key] = []
            if key in self._lockouts:
                del self._lockouts[key]
        else:
            self._attempts[key].append(time.time())

# Usage in ConfigManager:
class ConfigManager:
    def __init__(self, config_path: Path = Path("./bot_config.yaml")):
        self.config_path = Path(config_path)
        self._kdf_iterations = 600000
        self._rate_limiter = PasswordRateLimiter()
    
    def load_config(self, password: str) -> Config:
        # Check rate limit
        allowed, error = self._rate_limiter.check_allowed(str(self.config_path))
        if not allowed:
            raise SecurityError(error)
        
        try:
            # ... existing loading code ...
            config = Config.from_dict(data)
            
            # Decrypt private key
            if config.encrypted_private_key and config.salt:
                salt = base64.b64decode(config.salt)
                config.encrypted_private_key = self._decrypt_private_key(
                    config.encrypted_private_key,
                    password,
                    salt
                )
            
            # Record success
            self._rate_limiter.record_attempt(str(self.config_path), True)
            return config
            
        except Exception as e:
            # Record failure
            self._rate_limiter.record_attempt(str(self.config_path), False)
            raise
```

---

## Priority 2: Transaction Safety Hardening

### 2.1 Limit Token Approvals

**Current:**
```python
max_uint = 2**256 - 1
tx = token.functions.approve(spender, max_uint).build_transaction({...})
```

**Hardened:**
```python
class SafeTrader:
    """Trading with safe approval management"""
    
    APPROVAL_BUFFER = 1.01  # 1% buffer
    MAX_APPROVAL_AGE = 86400  # 24 hours in seconds
    
    def __init__(self):
        self._approvals: Dict[str, Dict] = {}  # token -> {spender, amount, timestamp}
    
    async def _ensure_approval(
        self, 
        token_address: str, 
        spender: str, 
        amount: int,
        force_exact: bool = False
    ):
        """Ensure token approval with safety limits"""
        token = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
        
        current_allowance = token.functions.allowance(
            self.wallet.address, spender
        ).call()
        
        if current_allowance >= amount:
            return  # Already approved
        
        # Calculate approval amount
        if force_exact:
            approval_amount = int(amount * self.APPROVAL_BUFFER)
        else:
            # Use exact amount + buffer instead of max uint
            approval_amount = int(amount * self.APPROVAL_BUFFER)
        
        # Double-check with user for large approvals
        if approval_amount > 10**24:  # Threshold for large amount
            confirm = input(
                f"⚠️  Large approval requested: {approval_amount}\n"
                f"Token: {token_address}\n"
                f"Spender: {spender}\n"
                f"Type 'APPROVE' to confirm: "
            )
            if confirm != "APPROVE":
                raise SecurityError("Approval cancelled by user")
        
        logger.info(f"Approving {spender} for {approval_amount} tokens...")
        
        tx = token.functions.approve(spender, approval_amount).build_transaction({
            'from': self.wallet.address,
            'nonce': self.wallet.get_nonce(),
            'gas': 100000,
            'gasPrice': self.web3.eth.gas_price,
            'chainId': 8453
        })
        
        signed_tx = self.wallet.sign_transaction(tx)
        tx_hash = self.wallet.send_raw_transaction(signed_tx)
        
        receipt = self.wallet.wait_for_transaction(tx_hash)
        
        if receipt['status'] != 1:
            raise TransactionError(f"Approval failed: {tx_hash}")
        
        # Record approval with timestamp for future cleanup
        self._approvals[token_address] = {
            'spender': spender,
            'amount': approval_amount,
            'timestamp': time.time()
        }
        
        logger.info(f"Approval successful: {tx_hash}")
        await asyncio.sleep(2)
    
    async def revoke_approvals(self):
        """Revoke all token approvals - call on shutdown"""
        for token_address, approval in self._approvals.items():
            try:
                token = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
                tx = token.functions.approve(approval['spender'], 0).build_transaction({
                    'from': self.wallet.address,
                    'nonce': self.wallet.get_nonce(),
                    'gas': 100000,
                    'gasPrice': self.web3.eth.gas_price,
                })
                signed_tx = self.wallet.sign_transaction(tx)
                tx_hash = self.wallet.send_raw_transaction(signed_tx)
                logger.info(f"Revoked approval for {token_address}: {tx_hash}")
            except Exception as e:
                logger.warning(f"Failed to revoke approval for {token_address}: {e}")
```

---

### 2.2 Enhanced Address Validation

```python
from web3 import Web3
from typing import Tuple

class AddressValidator:
    """Comprehensive address validation"""
    
    # Known suspicious patterns
    SUSPICIOUS_PATTERNS = [
        '0000000000',  # Too many zeros
        'deadbeef',    # Test addresses
        '12345678',    # Sequential
    ]
    
    @staticmethod
    def validate(address: str, require_checksum: bool = True) -> Tuple[bool, str]:
        """
        Comprehensive address validation
        
        Returns: (is_valid, error_message)
        """
        if not address:
            return False, "Address is empty"
        
        if not isinstance(address, str):
            return False, "Address must be a string"
        
        # Check basic format
        if not address.startswith('0x'):
            return False, "Address must start with 0x"
        
        if len(address) != 42:
            return False, f"Address length must be 42, got {len(address)}"
        
        # Check hex characters
        try:
            int(address[2:], 16)
        except ValueError:
            return False, "Address contains invalid hex characters"
        
        # Check checksum if required
        if require_checksum:
            try:
                # to_checksum_address will raise if checksum is invalid
                Web3.to_checksum_address(address)
            except ValueError:
                return False, "Address has invalid checksum (possible typo detected)"
        
        # Check for suspicious patterns
        addr_lower = address.lower()
        for pattern in AddressValidator.SUSPICIOUS_PATTERNS:
            if pattern in addr_lower:
                return False, f"Address contains suspicious pattern: {pattern}"
        
        return True, "Valid"
    
    @staticmethod
    def validate_with_confirm(address: str, context: str = "") -> bool:
        """Validate with user confirmation for high-risk addresses"""
        is_valid, error = AddressValidator.validate(address)
        
        if not is_valid:
            print(f"❌ Invalid address: {error}")
            return False
        
        # Show confirmation for addresses not in address book
        display_addr = f"{address[:10]}...{address[-8:]}"
        confirm = input(
            f"⚠️  Confirm address for {context}:\n"
            f"   {display_addr}\n"
            f"Type the last 4 characters to confirm: "
        )
        
        if confirm.lower() != address[-4:].lower():
            print("❌ Confirmation failed - address mismatch")
            return False
        
        return True
```

---

## Priority 3: Operational Security

### 3.1 Transaction Signing Confirmation

```python
class TransactionSafety:
    """Transaction safety controls"""
    
    def __init__(self, config: Config):
        self.config = config
        self._live_confirmed = False
        self._daily_limit_eth = 1.0  # Maximum daily spend
        self._daily_spent_eth = 0.0
        self._last_reset = datetime.now().date()
    
    def check_and_confirm(self, tx_value_eth: float, to_address: str) -> bool:
        """Check transaction safety and get confirmation"""
        
        # Reset daily limit if new day
        if datetime.now().date() != self._last_reset:
            self._daily_spent_eth = 0.0
            self._last_reset = datetime.now().date()
        
        # Check daily limit
        if self._daily_spent_eth + tx_value_eth > self._daily_limit_eth:
            print(f"❌ Daily limit exceeded ({self._daily_limit_eth} ETH)")
            return False
        
        # First live transaction confirmation
        if not self.config.dry_run and not self._live_confirmed:
            print("\n" + "="*60)
            print("⚠️  WARNING: LIVE TRANSACTION MODE")
            print("="*60)
            print(f"Transaction details:")
            print(f"  Value: {tx_value_eth} ETH")
            print(f"  To: {to_address}")
            print(f"  Network: Base Mainnet")
            print("="*60)
            
            confirm = input("\nType 'LIVE' to confirm this is a real transaction: ")
            if confirm != "LIVE":
                print("Transaction cancelled")
                return False
            
            self._live_confirmed = True
            print("✅ Live mode confirmed for this session\n")
        
        # High-value transaction confirmation
        if tx_value_eth > 0.1:
            confirm = input(
                f"⚠️  High value transaction: {tx_value_eth} ETH\n"
                f"Type CONFIRM to proceed: "
            )
            if confirm != "CONFIRM":
                return False
        
        self._daily_spent_eth += tx_value_eth
        return True
```

---

### 3.2 Secure Logging Configuration

```python
import logging
import re
from copy import deepcopy

class SecureLogger:
    """Logger that sanitizes sensitive data"""
    
    # Patterns to redact
    SENSITIVE_PATTERNS = [
        (r'0x[a-fA-F0-9]{64}', '[PRIVATE_KEY_REDACTED]'),  # Private keys
        (r'password["\']?\s*[:=]\s*["\'][^"\']+["\']', 'password=[REDACTED]'),
        (r'key["\']?\s*[:=]\s*["\'][^"\']{32,}["\']', 'key=[REDACTED]'),
    ]
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def _sanitize(self, msg: str) -> str:
        """Remove sensitive data from log message"""
        sanitized = str(msg)
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        return sanitized
    
    def info(self, msg: str, *args, **kwargs):
        self._logger.info(self._sanitize(msg), *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._logger.warning(self._sanitize(msg), *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._logger.error(self._sanitize(msg), *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        # For exceptions, still log full details but to secure log only
        self._logger.exception(self._sanitize(msg), *args, **kwargs)

# Usage:
secure_logger = SecureLogger(logger)
secure_logger.info(f"Transaction signed for {private_key}")  # Key will be redacted
```

---

## Priority 4: Environment Hardening

### 4.1 File Permissions

```bash
#!/bin/bash
# secure_setup.sh - Run after installation

# Set restrictive permissions on wallet files
chmod 600 .wallet.enc
chmod 600 bot_config.yaml
chmod 600 *.log

# Ensure directory is not world-readable
chmod 700 .

# Create secure log directory
mkdir -p logs
chmod 700 logs

# Set up log rotation with secure deletion
cat > /etc/logrotate.d/volume-bot << EOF
/home/user/volume_bot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0600 user user
    shred
}
EOF

echo "Permissions secured"
```

### 4.2 Environment Variable Security

```python
import os
from pathlib import Path

class SecureEnvironment:
    """Manage secure environment configuration"""
    
    @staticmethod
    def load_env_secure(env_file: str = ".env"):
        """Load env file with secure permissions check"""
        env_path = Path(env_file)
        
        if not env_path.exists():
            return
        
        # Check file permissions
        stat = env_path.stat()
        mode = stat.st_mode & 0o777
        
        if mode & 0o077:
            raise SecurityError(
                f"{env_file} has insecure permissions ({oct(mode)}). "
                "Run: chmod 600 {env_file}"
            )
        
        # Load with python-dotenv
        from dotenv import load_dotenv
        load_dotenv(env_path)
    
    @staticmethod
    def require_secure_env():
        """Ensure running in secure environment"""
        checks = []
        
        # Check for debugger
        if 'PYDEVD' in os.environ or 'DEBUG' in os.environ:
            checks.append("Debugger detected - do not use for production keys")
        
        # Check for core dumps
        import resource
        if resource.getrlimit(resource.RLIMIT_CORE)[0] > 0:
            checks.append("Core dumps enabled - disable with: ulimit -c 0")
        
        if checks:
            raise SecurityError("Insecure environment:\n" + "\n".join(checks))
```

---

## Migration Guide

### Upgrading from v1 to v2 Encryption

```python
# upgrade_wallet.py
import json
from pathlib import Path
from config import ConfigManager

def upgrade_wallet_encryption(old_file: str, new_file: str, password: str):
    """Upgrade wallet from v1 (SHA256) to v2 (PBKDF2) encryption"""
    
    # Load with old method
    with open(old_file, 'r') as f:
        old_data = json.load(f)
    
    # Decrypt old format
    import hashlib
    import base64
    from cryptography.fernet import Fernet
    
    key = hashlib.sha256(password.encode()).digest()
    key = base64.urlsafe_b64encode(key)
    f = Fernet(key)
    encrypted_bytes = base64.b64decode(old_data["encrypted"].encode())
    private_key = f.decrypt(encrypted_bytes).decode()
    
    # Save with new encryption
    manager = SecureKeyManager(new_file)
    if manager.encrypt_and_save(private_key, password):
        print("✅ Wallet upgraded successfully")
        print(f"New file: {new_file}")
        print(f"Backup old file: {old_file}.backup")
        Path(old_file).rename(f"{old_file}.backup")
    else:
        print("❌ Upgrade failed")
```

---

## Testing Hardened Implementation

```python
# test_security.py
import unittest
import time
from unittest.mock import patch

class TestSecurityHardening(unittest.TestCase):
    
    def test_kdf_iterations(self):
        """Verify KDF takes sufficient time"""
        manager = SecureKeyManager()
        salt = os.urandom(32)
        
        start = time.time()
        manager._derive_key("test_password", salt)
        duration = time.time() - start
        
        # Should take at least 100ms
        self.assertGreater(duration, 0.1)
    
    def test_rate_limiting(self):
        """Test rate limiter blocks after max attempts"""
        limiter = PasswordRateLimiter()
        
        # Should allow first 5 attempts
        for i in range(5):
            allowed, _ = limiter.check_allowed("test")
            self.assertTrue(allowed)
            limiter.record_attempt("test", False)
        
        # 6th attempt should be blocked
        allowed, error = limiter.check_allowed("test")
        self.assertFalse(allowed)
        self.assertIn("Locked", error)
    
    def test_address_validation(self):
        """Test address checksum validation"""
        # Valid checksum address
        valid = "0x696381f39F17cAD67032f5f52A4924ce84e51BA3"
        is_valid, _ = AddressValidator.validate(valid, require_checksum=True)
        self.assertTrue(is_valid)
        
        # Same address with wrong checksum
        invalid_checksum = "0x696381f39f17cad67032f5f52a4924ce84e51ba3"
        is_valid, error = AddressValidator.validate(invalid_checksum, require_checksum=True)
        self.assertFalse(is_valid)
        self.assertIn("checksum", error.lower())
    
    def test_secure_memory_clear(self):
        """Verify memory is cleared"""
        data = bytearray(b"sensitive_data_12345")
        original = bytes(data)
        
        # Clear the data
        for i in range(len(data)):
            data[i] = 0
        
        # Verify all zeros
        self.assertTrue(all(b == 0 for b in data))
        self.assertNotEqual(bytes(data), original)
```

---

*Implement these hardening measures in order of priority. Priority 1 items should be deployed immediately as they address critical vulnerabilities.*
