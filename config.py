"""
Configuration Management Module

Handles secure storage of configuration with encrypted private keys.
Uses Fernet symmetric encryption with password-derived keys.
"""

import os
import json
import base64
import getpass
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

import yaml
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Setup basic logging for this module
import logging
logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Bot configuration settings."""
    
    # Network
    rpc_url: str = "https://mainnet.base.org"
    chain_id: int = 8453
    
    # Token addresses
    compute_token: str = "0x696381f39F17cAD67032f5f52A4924ce84e51BA3"
    weth_address: str = "0x4200000000000000000000000000000000000006"
    
    # Uniswap V3 contracts on Base
    router_address: str = "0x2626664c2603336E57B271c5C0b26F421741e481"
    quoter_address: str = "0x3d4e44Eb1374240CE5F1B871ab261CD16335CB76"
    factory_address: str = "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"
    
    # Trading settings
    buy_amount_eth: float = 0.002  # ~$5-10 worth
    buy_interval_seconds: int = 300  # 5 minutes
    sell_after_buys: int = 10
    
    # Gas settings
    max_gas_price_gwei: float = 5.0
    slippage_percent: float = 2.0
    gas_limit_buffer: float = 1.2  # 20% buffer
    
    # Security
    encrypted_private_key: Optional[str] = None
    salt: Optional[str] = None
    
    # Operation
    dry_run: bool = False
    log_level: str = "INFO"
    log_file: str = "./bot.log"
    max_retries: int = 3
    retry_delay_seconds: int = 5
    health_check_interval: int = 60
    
    # Pool settings (Uniswap V3)
    pool_fee: int = 3000  # 0.3% fee tier
    
    # 1inch API (optional - if not set, uses direct DEX routing)
    oneinch_api_key: Optional[str] = None
    
    # 0x API (optional - preferred for V4 support)
    zerox_api_key: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding sensitive data)."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create Config from dictionary."""
        # Filter only valid fields
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)


class ConfigManager:
    """Manages configuration file with encrypted secrets."""
    
    def __init__(self, config_path: Path = Path("./bot_config.yaml")):
        self.config_path = Path(config_path)
        self._kdf_iterations = 480000  # OWASP recommended minimum
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self._kdf_iterations,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def _encrypt_private_key(self, private_key: str, password: str, salt: bytes) -> str:
        """Encrypt private key with password."""
        # Normalize private key (remove 0x prefix if present)
        pk_clean = private_key.strip()
        if pk_clean.startswith("0x"):
            pk_clean = pk_clean[2:]
        
        # Validate hex
        if len(pk_clean) != 64:
            raise ValueError("Private key must be 64 hex characters")
        try:
            int(pk_clean, 16)
        except ValueError:
            raise ValueError("Private key must be valid hex")
        
        key = self._derive_key(password, salt)
        f = Fernet(key)
        encrypted = f.encrypt(pk_clean.encode())
        return base64.b64encode(encrypted).decode()
    
    def _decrypt_private_key(self, encrypted_key: str, password: str, salt: bytes) -> str:
        """Decrypt private key with password."""
        key = self._derive_key(password, salt)
        f = Fernet(key)
        encrypted_bytes = base64.b64decode(encrypted_key.encode())
        decrypted = f.decrypt(encrypted_bytes)
        return "0x" + decrypted.decode()
    
    def create_config(
        self, 
        config_data: Dict[str, Any], 
        private_key: str, 
        password: str
    ) -> Config:
        """Create new configuration with encrypted private key."""
        # Generate random salt
        salt = os.urandom(16)
        salt_b64 = base64.b64encode(salt).decode()
        
        # Encrypt private key
        encrypted_key = self._encrypt_private_key(private_key, password, salt)
        
        # Create config object
        config_data["encrypted_private_key"] = encrypted_key
        config_data["salt"] = salt_b64
        
        config = Config.from_dict(config_data)
        
        # Save to file
        self._save_config(config)
        
        logger.info(f"Configuration created at {self.config_path}")
        return config
    
    def load_config(self, password: str) -> Config:
        """Load and decrypt configuration."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        config = Config.from_dict(data)
        
        # Decrypt private key for runtime use
        if config.encrypted_private_key and config.salt:
            salt = base64.b64decode(config.salt)
            config.encrypted_private_key = self._decrypt_private_key(
                config.encrypted_private_key,
                password,
                salt
            )
        
        logger.info("Configuration loaded successfully")
        return config
    
    def read_raw_config(self) -> Dict[str, Any]:
        """Read config without decrypting (for status checks)."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _save_config(self, config: Config):
        """Save configuration to YAML file."""
        # Ensure directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = config.to_dict()
        
        with open(self.config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        # Set restrictive permissions (owner read/write only)
        os.chmod(self.config_path, 0o600)
        
        logger.info(f"Configuration saved to {self.config_path}")
    
    def update_config(self, updates: Dict[str, Any], password: Optional[str] = None):
        """Update configuration values."""
        data = self.read_raw_config()
        data.update(updates)
        
        config = Config.from_dict(data)
        self._save_config(config)
        
        logger.info("Configuration updated")
    
    def rotate_password(self, old_password: str, new_password: str):
        """Change encryption password."""
        # Load with old password
        config = self.load_config(old_password)
        
        # Re-encrypt with new password
        private_key = config.encrypted_private_key
        
        # Generate new salt
        salt = os.urandom(16)
        salt_b64 = base64.b64encode(salt).decode()
        
        # Re-encrypt
        encrypted_key = self._encrypt_private_key(private_key, new_password, salt)
        
        # Update config
        data = self.read_raw_config()
        data["encrypted_private_key"] = encrypted_key
        data["salt"] = salt_b64
        
        config = Config.from_dict(data)
        self._save_config(config)
        
        logger.info("Password rotated successfully")


# Default configuration template
DEFAULT_CONFIG = """
# $COMPUTE Volume Bot Configuration
# This file contains encrypted credentials - keep it secure!

rpc_url: https://mainnet.base.org
chain_id: 8453

# Token Contracts
compute_token: "0x696381f39F17cAD67032f5f52A4924ce84e51BA3"
weth_address: "0x4200000000000000000000000000000000000006"

# Uniswap V3 Contracts
router_address: "0x2626664c2603336E57B271c5C0b26F421741e481"
quoter_address: "0x3d4e44Eb1374240CE5F1B871ab261CD16335CB76"
factory_address: "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"

# Trading Parameters
buy_amount_eth: 0.002
buy_interval_seconds: 300
sell_after_buys: 10
pool_fee: 3000

# Gas Settings
max_gas_price_gwei: 5.0
slippage_percent: 2.0
gas_limit_buffer: 1.2

# Operation Settings
dry_run: false
log_level: INFO
log_file: ./bot.log
max_retries: 3
retry_delay_seconds: 5
health_check_interval: 60

# Encrypted credentials (DO NOT MODIFY)
encrypted_private_key: null
salt: null
""".strip()
