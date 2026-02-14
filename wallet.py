"""
Wallet Module - Secure Key Management
=====================================
Handles encrypted storage of private keys and Web3 interactions.

Security:
- PBKDF2-HMAC-SHA256 key derivation (600k iterations)
- Fernet (AES-128-CBC) encryption
- Unique salt per encryption
- File permissions 0o600 (owner-only)
"""

import os
import json
import base64
import secrets
from pathlib import Path
from typing import Optional
from web3 import Web3
from eth_account import Account
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecureKeyManager:
    """
    Manages secure encryption and decryption of private keys.
    
    Uses PBKDF2-HMAC-SHA256 with 600,000 iterations for key derivation,
    and Fernet (AES-128-CBC) for encryption.
    """
    
    KEY_FILE = ".bot_wallet.enc"
    ITERATIONS = 600_000  # OWASP recommended minimum
    
    def __init__(self, key_file: Optional[str] = None):
        """
        Initialize key manager.
        
        Args:
            key_file: Path to encrypted key file (default: .bot_wallet.enc)
        """
        self.key_file = Path(key_file or self.KEY_FILE)
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: User password
            salt: Random salt (16 bytes)
            
        Returns:
            URL-safe base64-encoded key for Fernet
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.ITERATIONS,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt_and_save(self, private_key: str, password: str) -> bool:
        """
        Encrypt and save a private key.
        
        Args:
            private_key: Ethereum private key (with 0x prefix)
            password: Encryption password
            
        Returns:
            True if successful
        """
        try:
            # Generate random salt
            salt = secrets.token_bytes(16)
            
            # Derive key
            key = self._derive_key(password, salt)
            
            # Encrypt
            f = Fernet(key)
            encrypted = f.encrypt(private_key.encode())
            
            # Store salt + encrypted data
            data = {
                "salt": base64.b64encode(salt).decode(),
                "encrypted_key": encrypted.decode(),
                "version": 2  # Version for future migrations
            }
            
            # Save with restricted permissions
            with open(self.key_file, 'w') as f:
                json.dump(data, f)
            
            # Set owner-only permissions (Unix)
            os.chmod(self.key_file, 0o600)
            
            return True
            
        except Exception as e:
            print(f"Error saving encrypted key: {e}")
            return False
    
    def load_and_decrypt(self, password: str) -> Optional[str]:
        """
        Load and decrypt the private key.
        
        Args:
            password: Encryption password
            
        Returns:
            Decrypted private key or None if failed
        """
        try:
            if not self.key_file.exists():
                print("No wallet file found. Run setup first.")
                return None
            
            with open(self.key_file, 'r') as f:
                data = json.load(f)
            
            # Extract salt and encrypted key
            salt = base64.b64decode(data["salt"])
            encrypted_key = data["encrypted_key"].encode()
            
            # Derive key
            key = self._derive_key(password, salt)
            
            # Decrypt
            f = Fernet(key)
            decrypted = f.decrypt(encrypted_key)
            
            return decrypted.decode()
            
        except Exception as e:
            print(f"Error decrypting key: {e}")
            return None
    
    def exists(self) -> bool:
        """Check if encrypted key file exists."""
        return self.key_file.exists()
    
    def delete(self) -> bool:
        """Delete the encrypted key file."""
        try:
            if self.key_file.exists():
                self.key_file.unlink()
            return True
        except Exception as e:
            print(f"Error deleting key file: {e}")
            return False


class SecureWallet:
    """
    Wrapper for Web3 interactions with encrypted key storage.
    Provides a unified interface for the trader module.
    """
    
    def __init__(self, private_key: str, rpc_url: str = "https://mainnet.base.org"):
        """
        Initialize wallet with private key.
        
        Args:
            private_key: Ethereum private key
            rpc_url: RPC endpoint URL
        """
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self._private_key = private_key
    
    def get_web3(self) -> Web3:
        """Get Web3 instance."""
        return self.web3
    
    def get_address(self) -> str:
        """Get wallet address."""
        return self.address
    
    def sign_transaction(self, transaction_dict: dict) -> dict:
        """Sign a transaction."""
        return self.account.sign_transaction(transaction_dict)
    
    def get_eth_balance(self) -> float:
        """Get ETH balance."""
        balance_wei = self.web3.eth.get_balance(self.address)
        return float(self.web3.from_wei(balance_wei, 'ether'))
    
    def get_token_balance(self, token_address: str) -> float:
        """Get ERC20 token balance."""
        # Minimal ERC20 ABI for balanceOf
        erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            }
        ]
        
        token = self.web3.eth.contract(
            address=self.web3.to_checksum_address(token_address),
            abi=erc20_abi
        )
        
        balance = token.functions.balanceOf(self.address).call()
        decimals = token.functions.decimals().call()
        
        return balance / (10 ** decimals)
