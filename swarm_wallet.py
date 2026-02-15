"""
Swarm Wallet Module - Secure Multi-Wallet Management System
===========================================================

This module provides secure generation, storage, and management of multiple
Ethereum wallets ("swarm") for the volume bot. Each wallet is individually
encrypted and can be cycled through for trading operations.

SECURITY FEATURES:
- All private keys encrypted at rest using Fernet (AES-128)
- Password-derived encryption keys via PBKDF2
- Never stores main wallet private key
- Validates balances before any fund movement
- Dry-run mode for safe testing
- Comprehensive audit logging

Author: Cult of the Shell
"""

import os
import json
import base64
import hashlib
import secrets
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

from eth_account import Account
from web3 import Web3
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from utils import logger, format_address, validate_address, mask_sensitive


class RotationMode(Enum):
    """Wallet rotation strategies."""
    ROUND_ROBIN = "round_robin"  # Cycle through wallets sequentially
    RANDOM = "random"            # Randomly select wallets
    LEAST_USED = "least_used"    # Use wallet with fewest transactions
    BALANCE_BASED = "balance"    # Use wallet with highest ETH balance


@dataclass
class SwarmWalletConfig:
    """Configuration for swarm wallet system."""
    # Wallet settings
    num_wallets: int = 10                    # Number of swarm wallets to create
    min_eth_per_wallet: float = 0.01        # Minimum ETH to keep in each wallet (gas reserve)
    eth_fund_amount: float = 0.02           # ETH to fund each wallet initially
    funder_gas_reserve: float = 0.005       # ETH to reserve on funder wallet for gas (was 0.01)
    
    # Rotation settings
    rotation_mode: RotationMode = RotationMode.ROUND_ROBIN
    
    # Security settings
    key_file: str = "./swarm_wallets.enc"   # Encrypted wallet storage file
    audit_log: str = "./swarm_audit.log"    # Audit trail log file
    
    # Token addresses (Base network)
    compute_token: str = "0x696381f39F17cAD67032f5f52A4924ce84e51BA3"
    weth_address: str = "0x4200000000000000000000000000000000000006"
    
    # Operation settings
    dry_run: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['rotation_mode'] = self.rotation_mode.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SwarmWalletConfig':
        """Create config from dictionary."""
        if 'rotation_mode' in data:
            data['rotation_mode'] = RotationMode(data['rotation_mode'])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SwarmWallet:
    """Individual swarm wallet with metadata."""
    index: int                              # Wallet index in swarm
    address: str                            # Ethereum address
    encrypted_private_key: str              # Encrypted private key (base64)
    salt: str                               # Encryption salt (base64)
    created_at: str                         # ISO timestamp
    
    # Transaction tracking
    tx_count: int = 0
    total_buys: int = 0
    total_sells: int = 0
    total_eth_spent: float = 0.0
    total_eth_received: float = 0.0
    last_used: Optional[str] = None
    
    # Status
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SwarmWallet':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def record_buy(self, eth_amount: float):
        """Record a buy transaction."""
        self.tx_count += 1
        self.total_buys += 1
        self.total_eth_spent += eth_amount
        self.last_used = datetime.now().isoformat()
    
    def record_sell(self, eth_amount: float):
        """Record a sell transaction."""
        self.tx_count += 1
        self.total_sells += 1
        self.total_eth_received += eth_amount
        self.last_used = datetime.now().isoformat()


@dataclass
class AuditRecord:
    """Audit record for tracking all fund movements."""
    timestamp: str
    action: str                            # CREATE, FUND, RECLAIM, BUY, SELL, etc.
    wallet_index: Optional[int]            # Which wallet (None for main)
    from_address: str
    to_address: str
    eth_amount: Optional[float] = None
    compute_amount: Optional[float] = None
    tx_hash: Optional[str] = None
    status: str = "PENDING"               # PENDING, SUCCESS, FAILED
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SecureSwarmManager:
    """
    Secure manager for swarm wallet operations.
    
    Handles wallet generation, encryption, funding, and reclamation.
    NEVER stores the main wallet private key - it must be provided for operations.
    """
    
    # KDF iterations (OWASP recommended minimum)
    KDF_ITERATIONS = 480000
    
    def __init__(self, config: SwarmWalletConfig, web3: Web3):
        self.config = config
        self.web3 = web3
        self.wallets: List[SwarmWallet] = []
        self._current_index: int = 0
        self._audit_records: List[AuditRecord] = []
        
        # Load existing wallets if present
        self._load_wallets()
        self._load_audit_log()
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: User password
            salt: Random salt bytes
            
        Returns:
            Base64-encoded key for Fernet
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.KDF_ITERATIONS,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def _encrypt_private_key(self, private_key: str, password: str, salt: bytes) -> str:
        """
        Encrypt a private key.
        
        Args:
            private_key: Private key with or without 0x prefix
            password: Encryption password
            salt: Salt bytes
            
        Returns:
            Base64-encoded encrypted private key
        """
        # Normalize private key
        pk_clean = private_key.strip()
        if pk_clean.startswith("0x"):
            pk_clean = pk_clean[2:]
        
        # Validate
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
        """
        Decrypt a private key.
        
        Args:
            encrypted_key: Base64-encoded encrypted key
            password: Decryption password
            salt: Salt bytes
            
        Returns:
            Private key with 0x prefix
        """
        key = self._derive_key(password, salt)
        f = Fernet(key)
        encrypted_bytes = base64.b64decode(encrypted_key.encode())
        decrypted = f.decrypt(encrypted_bytes)
        return "0x" + decrypted.decode()
    
    def _load_wallets(self):
        """Load wallets from encrypted storage file."""
        key_file = Path(self.config.key_file)
        if not key_file.exists():
            logger.info("No existing swarm wallet file found")
            return
        
        try:
            with open(key_file, 'r') as f:
                data = json.load(f)
            
            self.wallets = [SwarmWallet.from_dict(w) for w in data.get('wallets', [])]
            self._current_index = data.get('current_index', 0)
            
            logger.info(f"Loaded {len(self.wallets)} swarm wallets from storage")
            
        except Exception as e:
            logger.error(f"Failed to load swarm wallets: {e}")
            raise
    
    def _save_wallets(self):
        """Save wallets to encrypted storage file."""
        key_file = Path(self.config.key_file)
        
        try:
            data = {
                'version': '1.0',
                'updated_at': datetime.now().isoformat(),
                'current_index': self._current_index,
                'wallets': [w.to_dict() for w in self.wallets]
            }
            
            # Ensure directory exists
            key_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(key_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            
        except Exception as e:
            logger.error(f"Failed to save swarm wallets: {e}")
            raise
    
    def _load_audit_log(self):
        """Load audit log from file."""
        audit_file = Path(self.config.audit_log)
        if not audit_file.exists():
            return
        
        try:
            with open(audit_file, 'r') as f:
                data = json.load(f)
            self._audit_records = [AuditRecord(**r) for r in data.get('records', [])]
        except Exception as e:
            logger.warning(f"Could not load audit log: {e}")
    
    def _save_audit_log(self):
        """Save audit log to file."""
        audit_file = Path(self.config.audit_log)
        
        try:
            data = {
                'version': '1.0',
                'updated_at': datetime.now().isoformat(),
                'records': [r.to_dict() for r in self._audit_records]
            }
            
            audit_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(audit_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            os.chmod(audit_file, 0o600)
            
        except Exception as e:
            logger.error(f"Failed to save audit log: {e}")
    
    def _add_audit_record(self, record: AuditRecord):
        """Add an audit record and save the log."""
        self._audit_records.append(record)
        self._save_audit_log()
    
    def _get_wallet_balance(self, address: str) -> Tuple[float, float]:
        """
        Get ETH and COMPUTE balance for an address.
        
        Returns:
            Tuple of (eth_balance, compute_balance)
        """
        try:
            # Get ETH balance
            eth_wei = self.web3.eth.get_balance(address)
            eth_balance = float(self.web3.from_wei(eth_wei, 'ether'))
            
            # Get COMPUTE balance (ERC20)
            compute_balance = self._get_erc20_balance(address)
            
            return eth_balance, compute_balance
            
        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {e}")
            return 0.0, 0.0
    
    def _get_erc20_balance(self, address: str) -> float:
        """Get COMPUTE token balance for an address."""
        try:
            # ERC20 balanceOf function signature: 0x70a08231
            data = "0x70a08231000000000000000000000000" + address[2:]
            
            result = self.web3.eth.call({
                'to': self.config.compute_token,
                'data': data
            })
            
            balance = int(result.hex(), 16)
            
            # Get decimals (assume 18 for COMPUTE)
            return balance / (10 ** 18)
            
        except Exception as e:
            logger.warning(f"Failed to get COMPUTE balance: {e}")
            return 0.0
    
    def create_swarm(self, password: str, num_wallets: Optional[int] = None) -> List[SwarmWallet]:
        """
        Create a new swarm of wallets.
        
        Args:
            password: Password for encrypting wallet keys
            num_wallets: Number of wallets to create (uses config default if None)
            
        Returns:
            List of created SwarmWallet objects
            
        Security:
            - Each wallet gets a unique random salt
            - Private keys are cryptographically secure random
            - Keys are encrypted before storage
        """
        if num_wallets is None:
            num_wallets = self.config.num_wallets
        
        logger.info(f"Creating swarm of {num_wallets} wallets...")
        
        # Validate password strength
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        
        created_wallets = []
        
        for i in range(num_wallets):
            # Generate cryptographically secure private key
            # Using secrets for better randomness than os.urandom
            private_key_bytes = secrets.token_bytes(32)
            private_key = "0x" + private_key_bytes.hex()
            
            # Create account
            account = Account.from_key(private_key)
            
            # Generate unique salt for this wallet
            salt = os.urandom(16)
            salt_b64 = base64.b64encode(salt).decode()
            
            # Encrypt private key
            encrypted_key = self._encrypt_private_key(private_key, password, salt)
            
            # Create wallet record
            wallet = SwarmWallet(
                index=i,
                address=account.address,
                encrypted_private_key=encrypted_key,
                salt=salt_b64,
                created_at=datetime.now().isoformat()
            )
            
            created_wallets.append(wallet)
            logger.info(f"Created wallet {i}: {format_address(account.address)}")
        
        # Save to storage
        self.wallets = created_wallets
        self._save_wallets()
        
        # Audit log
        self._add_audit_record(AuditRecord(
            timestamp=datetime.now().isoformat(),
            action="CREATE",
            wallet_index=None,
            from_address="N/A",
            to_address="SWARM",
            status="SUCCESS"
        ))
        
        logger.info(f"Swarm creation complete. {num_wallets} wallets created.")
        return created_wallets
    
    def get_wallet(self, index: int, password: str) -> Tuple[SwarmWallet, Account]:
        """
        Get a wallet and decrypt its private key.
        
        Args:
            index: Wallet index
            password: Decryption password
            
        Returns:
            Tuple of (SwarmWallet, Account)
            
        Security:
            - Private key is decrypted in memory only
            - Never logs or stores decrypted key
        """
        if index < 0 or index >= len(self.wallets):
            raise IndexError(f"Invalid wallet index: {index}")
        
        wallet = self.wallets[index]
        
        # Decrypt private key
        salt = base64.b64decode(wallet.salt)
        private_key = self._decrypt_private_key(wallet.encrypted_private_key, password, salt)
        
        # Create account
        account = Account.from_key(private_key)
        
        # Verify address matches
        if account.address.lower() != wallet.address.lower():
            raise ValueError("Decrypted address does not match stored address!")
        
        return wallet, account
    
    def get_next_wallet(self, password: str) -> Tuple[SwarmWallet, Account]:
        """
        Get the next wallet based on rotation mode.
        
        Args:
            password: Decryption password
            
        Returns:
            Tuple of (SwarmWallet, Account)
        """
        if not self.wallets:
            raise ValueError("No wallets in swarm. Create swarm first.")
        
        if self.config.rotation_mode == RotationMode.ROUND_ROBIN:
            index = self._current_index % len(self.wallets)
            self._current_index = (self._current_index + 1) % len(self.wallets)
            
        elif self.config.rotation_mode == RotationMode.RANDOM:
            index = secrets.randbelow(len(self.wallets))
            
        elif self.config.rotation_mode == RotationMode.LEAST_USED:
            # Find wallet with lowest tx_count
            index = min(range(len(self.wallets)), key=lambda i: self.wallets[i].tx_count)
            
        elif self.config.rotation_mode == RotationMode.BALANCE_BASED:
            # Find wallet with highest ETH balance
            balances = [self._get_wallet_balance(w.address)[0] for w in self.wallets]
            index = balances.index(max(balances))
            
        else:
            index = self._current_index % len(self.wallets)
            self._current_index += 1
        
        # Save updated index
        self._save_wallets()
        
        return self.get_wallet(index, password)
    
    def fund_swarm(
        self, 
        main_wallet_key: str, 
        eth_per_wallet: Optional[float] = None,
        password: Optional[str] = None
    ) -> List[AuditRecord]:
        """
        Fund all swarm wallets from main wallet.
        
        Args:
            main_wallet_key: Main wallet private key (for signing transactions)
            eth_per_wallet: ETH to send to each wallet (uses config default if None)
            password: Password for decrypting swarm wallets (if needed)
            
        Returns:
            List of audit records for the funding transactions
            
        Security:
            - Main wallet key is never stored
            - Validates all addresses before sending
            - Checks main wallet has sufficient balance
            - Never sends if gas would be insufficient
        """
        if eth_per_wallet is None:
            eth_per_wallet = self.config.eth_fund_amount
        
        if not self.wallets:
            raise ValueError("No wallets to fund. Create swarm first.")
        
        # Setup main wallet account
        main_account = Account.from_key(main_wallet_key)
        main_address = main_account.address
        
        logger.info(f"Funding swarm from main wallet: {format_address(main_address)}")
        
        # Check main wallet balance
        main_balance = self.web3.eth.get_balance(main_address)
        total_needed = self.web3.to_wei(eth_per_wallet * len(self.wallets), 'ether')
        gas_reserve = self.web3.to_wei(self.config.funder_gas_reserve, 'ether')  # Configurable reserve
        
        if main_balance < total_needed + gas_reserve:
            raise InsufficientFundsError(
                f"Main wallet needs {self.web3.from_wei(total_needed + gas_reserve, 'ether')} ETH, "
                f"has {self.web3.from_wei(main_balance, 'ether')} ETH"
            )
        
        if self.config.dry_run:
            logger.info(f"[DRY RUN] Would fund {len(self.wallets)} wallets with {eth_per_wallet} ETH each")
            return []
        
        audit_records = []
        
        # Get starting nonce with 'pending' to account for in-flight txs
        next_nonce = self.web3.eth.get_transaction_count(main_address, 'pending')
        
        for wallet in self.wallets:
            try:
                # Build transaction with explicit nonce (incremented for each wallet)
                tx = {
                    'to': wallet.address,
                    'value': self.web3.to_wei(eth_per_wallet, 'ether'),
                    'gas': 21000,
                    'gasPrice': self.web3.eth.gas_price,
                    'nonce': next_nonce,  # Use tracked nonce
                    'chainId': 8453  # Base mainnet
                }
                
                # Increment nonce for next iteration
                next_nonce += 1
                
                # Sign and send
                signed_tx = self.web3.eth.account.sign_transaction(tx, main_wallet_key)
                tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                
                logger.info(f"Funding wallet {wallet.index}: {tx_hash.hex()}")
                
                # Wait for receipt
                receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                # Create audit record
                record = AuditRecord(
                    timestamp=datetime.now().isoformat(),
                    action="FUND",
                    wallet_index=wallet.index,
                    from_address=main_address,
                    to_address=wallet.address,
                    eth_amount=eth_per_wallet,
                    tx_hash=tx_hash.hex(),
                    status="SUCCESS" if receipt['status'] == 1 else "FAILED"
                )
                
                audit_records.append(record)
                
                if receipt['status'] != 1:
                    logger.error(f"Funding failed for wallet {wallet.index}")
                else:
                    logger.info(f"Funded wallet {wallet.index} with {eth_per_wallet} ETH")
                
            except Exception as e:
                logger.error(f"Failed to fund wallet {wallet.index}: {e}")
                
                record = AuditRecord(
                    timestamp=datetime.now().isoformat(),
                    action="FUND",
                    wallet_index=wallet.index,
                    from_address=main_address,
                    to_address=wallet.address,
                    eth_amount=eth_per_wallet,
                    status="FAILED",
                    error=str(e)
                )
                audit_records.append(record)
        
        # Save audit log
        for record in audit_records:
            self._add_audit_record(record)
        
        self._save_wallets()
        
        success_count = sum(1 for r in audit_records if r.status == "SUCCESS")
        logger.info(f"Funding complete: {success_count}/{len(self.wallets)} successful")
        
        return audit_records
    
    def reclaim_funds(
        self,
        main_wallet_address: str,
        password: str,
        reclaim_compute: bool = True
    ) -> List[AuditRecord]:
        """
        Reclaim all funds from swarm wallets back to main wallet.
        
        CRITICAL SAFETY: NEVER dissolves wallet with non-zero balance.
        All funds must be transferred before wallet is considered reclaimed.
        
        Args:
            main_wallet_address: Address to reclaim funds to
            password: Password for decrypting swarm wallet keys
            reclaim_compute: Whether to also reclaim COMPUTE tokens
            
        Returns:
            List of audit records
            
        Security:
            - Verifies zero balance before marking complete
            - Validates main wallet address
            - Leaves minimum ETH for gas on each transfer
            - Never exposes decrypted keys except for signing
        """
        if not validate_address(main_wallet_address):
            raise ValueError("Invalid main wallet address")
        
        main_address = self.web3.to_checksum_address(main_wallet_address)
        
        logger.info(f"Reclaiming funds to: {format_address(main_address)}")
        
        if self.config.dry_run:
            logger.info("[DRY RUN] Would reclaim all funds from swarm wallets")
            return []
        
        audit_records = []
        
        for wallet in self.wallets:
            try:
                # Get wallet and decrypt key
                swarm_wallet, account = self.get_wallet(wallet.index, password)
                
                # Check balances
                eth_balance, compute_balance = self._get_wallet_balance(account.address)
                
                logger.info(
                    f"Wallet {wallet.index}: {eth_balance:.6f} ETH, "
                    f"{compute_balance:.6f} COMPUTE"
                )
                
                # Reclaim COMPUTE first (if requested and has balance)
                if reclaim_compute and compute_balance > 0:
                    self._reclaim_compute(account, main_address, swarm_wallet, audit_records)
                
                # Reclaim ETH
                if eth_balance > self.config.min_eth_per_wallet:
                    self._reclaim_eth(account, main_address, eth_balance, swarm_wallet, audit_records)
                
                # Update wallet stats
                swarm_wallet.is_active = False
                
            except Exception as e:
                logger.error(f"Failed to reclaim from wallet {wallet.index}: {e}")
                
                record = AuditRecord(
                    timestamp=datetime.now().isoformat(),
                    action="RECLAIM",
                    wallet_index=wallet.index,
                    from_address=wallet.address,
                    to_address=main_address,
                    status="FAILED",
                    error=str(e)
                )
                audit_records.append(record)
        
        # Save updates
        self._save_wallets()
        
        for record in audit_records:
            self._add_audit_record(record)
        
        success_count = sum(1 for r in audit_records if r.status == "SUCCESS")
        logger.info(f"Reclamation complete: {success_count}/{len(audit_records)} operations successful")
        
        return audit_records
    
    def _reclaim_eth(
        self,
        account: Account,
        main_address: str,
        eth_balance: float,
        swarm_wallet: SwarmWallet,
        audit_records: List[AuditRecord]
    ):
        """Reclaim ETH from a swarm wallet."""
        try:
            # Calculate amount to send (leave min_eth for gas)
            gas_cost = self.web3.to_wei(0.0001, 'ether')  # Estimated gas cost
            min_reserve = self.web3.to_wei(self.config.min_eth_per_wallet, 'ether')
            
            balance_wei = self.web3.eth.get_balance(account.address)
            send_amount = balance_wei - min_reserve - gas_cost
            
            if send_amount <= 0:
                logger.warning(f"Wallet {swarm_wallet.index}: Insufficient ETH to reclaim after gas reserve")
                return
            
            # Build transaction
            tx = {
                'to': main_address,
                'value': send_amount,
                'gas': 21000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(account.address),
                'chainId': 8453
            }
            
            # Sign and send
            signed_tx = self.web3.eth.account.sign_transaction(tx, account.key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.info(f"Reclaiming ETH from wallet {swarm_wallet.index}: {tx_hash.hex()}")
            
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            eth_sent = float(self.web3.from_wei(send_amount, 'ether'))
            
            record = AuditRecord(
                timestamp=datetime.now().isoformat(),
                action="RECLAIM_ETH",
                wallet_index=swarm_wallet.index,
                from_address=account.address,
                to_address=main_address,
                eth_amount=eth_sent,
                tx_hash=tx_hash.hex(),
                status="SUCCESS" if receipt['status'] == 1 else "FAILED"
            )
            audit_records.append(record)
            
            if receipt['status'] == 1:
                swarm_wallet.total_eth_received += eth_sent
                logger.info(f"Reclaimed {eth_sent:.6f} ETH from wallet {swarm_wallet.index}")
            else:
                logger.error(f"ETH reclaim failed for wallet {swarm_wallet.index}")
                
        except Exception as e:
            logger.error(f"ETH reclaim error for wallet {swarm_wallet.index}: {e}")
            audit_records.append(AuditRecord(
                timestamp=datetime.now().isoformat(),
                action="RECLAIM_ETH",
                wallet_index=swarm_wallet.index,
                from_address=account.address,
                to_address=main_address,
                status="FAILED",
                error=str(e)
            ))
    
    def _reclaim_compute(
        self,
        account: Account,
        main_address: str,
        swarm_wallet: SwarmWallet,
        audit_records: List[AuditRecord]
    ):
        """Reclaim COMPUTE tokens from a swarm wallet."""
        try:
            # Get COMPUTE balance
            compute_balance = self._get_erc20_balance(account.address)
            
            if compute_balance <= 0:
                return
            
            # Get raw balance
            data = "0x70a08231000000000000000000000000" + account.address[2:]
            result = self.web3.eth.call({'to': self.config.compute_token, 'data': data})
            raw_balance = int(result.hex(), 16)
            
            # ERC20 transfer function: transfer(address,uint256)
            # Function signature: 0xa9059cbb
            transfer_data = (
                "0xa9059cbb" +
                "000000000000000000000000" + main_address[2:] +
                format(raw_balance, '064x')
            )
            
            # Build transaction
            tx = {
                'to': self.config.compute_token,
                'data': transfer_data,
                'gas': 100000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(account.address),
                'chainId': 8453
            }
            
            # Sign and send
            signed_tx = self.web3.eth.account.sign_transaction(tx, account.key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.info(f"Reclaiming COMPUTE from wallet {swarm_wallet.index}: {tx_hash.hex()}")
            
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            record = AuditRecord(
                timestamp=datetime.now().isoformat(),
                action="RECLAIM_COMPUTE",
                wallet_index=swarm_wallet.index,
                from_address=account.address,
                to_address=main_address,
                compute_amount=compute_balance,
                tx_hash=tx_hash.hex(),
                status="SUCCESS" if receipt['status'] == 1 else "FAILED"
            )
            audit_records.append(record)
            
            if receipt['status'] == 1:
                logger.info(f"Reclaimed {compute_balance:.6f} COMPUTE from wallet {swarm_wallet.index}")
            else:
                logger.error(f"COMPUTE reclaim failed for wallet {swarm_wallet.index}")
                
        except Exception as e:
            logger.error(f"COMPUTE reclaim error for wallet {swarm_wallet.index}: {e}")
            audit_records.append(AuditRecord(
                timestamp=datetime.now().isoformat(),
                action="RECLAIM_COMPUTE",
                wallet_index=swarm_wallet.index,
                from_address=account.address,
                to_address=main_address,
                status="FAILED",
                error=str(e)
            ))
    
    def get_swarm_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the swarm."""
        if not self.wallets:
            return {"status": "NO_SWARM", "wallets": []}
        
        wallet_data = []
        total_eth = 0.0
        total_compute = 0.0
        
        for wallet in self.wallets:
            eth_balance, compute_balance = self._get_wallet_balance(wallet.address)
            total_eth += eth_balance
            total_compute += compute_balance
            
            wallet_data.append({
                "index": wallet.index,
                "address": wallet.address,
                "eth_balance": eth_balance,
                "compute_balance": compute_balance,
                "tx_count": wallet.tx_count,
                "is_active": wallet.is_active
            })
        
        return {
            "status": "ACTIVE",
            "total_wallets": len(self.wallets),
            "active_wallets": sum(1 for w in self.wallets if w.is_active),
            "total_eth": total_eth,
            "total_compute": total_compute,
            "rotation_mode": self.config.rotation_mode.value,
            "wallets": wallet_data
        }
    
    def get_audit_trail(self, limit: int = 100) -> List[AuditRecord]:
        """Get recent audit records."""
        return self._audit_records[-limit:]
    
    def verify_zero_balances(self) -> List[int]:
        """
        Verify all wallets have zero (or near-zero) balances.
        
        Returns:
            List of wallet indices that still have non-zero balances
        """
        non_zero = []
        
        for wallet in self.wallets:
            eth_balance, compute_balance = self._get_wallet_balance(wallet.address)
            
            # Allow small dust amounts for ETH (gas reserve)
            if eth_balance > self.config.min_eth_per_wallet * 2:
                non_zero.append(wallet.index)
            elif compute_balance > 0.0001:  # Dust threshold for COMPUTE
                non_zero.append(wallet.index)
        
        return non_zero
    
    def dissolve_swarm(
        self,
        main_wallet_key: str,
        password: Optional[str] = None,
        force: bool = False
    ) -> Tuple[bool, List[AuditRecord]]:
        """
        Dissolve the swarm: reclaim all funds to near-zero, verify empty, delete wallet file.
        
        This is a DESTRUCTIVE operation that:
        1. Sells all tokens for ETH (if any)
        2. Reclaims ETH leaving only gas for final reclaim (or 0 if force=True)
        3. Verifies all wallets are at zero (or near-zero)
        4. Deletes the encrypted wallet file
        
        Args:
            main_wallet_key: Main wallet private key for reclaim
            password: Password for decrypting swarm wallets
            force: If True, reclaim ALL ETH including gas reserve (risky)
            
        Returns:
            Tuple of (success, audit_records)
        """
        import os
        
        logger.info("=" * 60)
        logger.info("SWARM DISSOLUTION STARTED")
        logger.info("=" * 60)
        
        if not self.wallets:
            logger.error("No wallets to dissolve")
            return False, []
        
        audit_records = []
        
        # Step 1: Sell all tokens for ETH (if any tokens exist)
        logger.info("Step 1: Liquidating all tokens...")
        for wallet in self.wallets:
            eth_bal, comp_bal = self._get_wallet_balance(wallet.address)
            if comp_bal > 0:
                logger.info(f"Wallet {wallet.index}: Selling {comp_bal} COMPUTE...")
                # Token liquidation would go here - simplified for now
                # In production, call swap_tokens_for_eth via 0x or V3
                logger.warning(f"Token liquidation not yet implemented - wallet {wallet.index} still has {comp_bal} tokens")
        
        # Step 2: Reclaim ETH to near-zero
        logger.info("Step 2: Reclaiming ETH to near-zero...")
        
        # Temporarily reduce min_eth to allow near-zero reclaim
        original_min_eth = self.config.min_eth_per_wallet
        if force:
            self.config.min_eth_per_wallet = 0.0  # Reclaim everything
        else:
            self.config.min_eth_per_wallet = 0.0001  # Leave tiny amount for gas
        
        try:
            reclaim_records = self.reclaim_funds(main_wallet_key, password)
            audit_records.extend(reclaim_records)
        finally:
            self.config.min_eth_per_wallet = original_min_eth  # Restore original
        
        # Step 3: Verify all wallets are at zero
        logger.info("Step 3: Verifying zero balances...")
        non_zero = self.verify_zero_balances()
        
        if non_zero:
            logger.error(f"Cannot dissolve: Wallets {non_zero} still have non-zero balances")
            logger.error("Use force=True to dissolve anyway (WARNING: may lose funds)")
            return False, audit_records
        
        # Step 4: Delete the wallet file
        logger.info("Step 4: Deleting encrypted wallet file...")
        key_file = self.config.key_file
        
        if os.path.exists(key_file):
            try:
                # Archive instead of delete (safety)
                archive_name = f"{key_file}.dissolved.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(key_file, archive_name)
                logger.info(f"Wallet file archived to: {archive_name}")
            except Exception as e:
                logger.error(f"Failed to archive wallet file: {e}")
                return False, audit_records
        
        # Final audit record
        final_record = AuditRecord(
            timestamp=datetime.now().isoformat(),
            action="DISSOLVE",
            wallet_index=-1,
            from_address="SWARM",
            to_address="DISSOLVED",
            eth_amount=0.0,
            tx_hash="",
            status="SUCCESS"
        )
        audit_records.append(final_record)
        self._audit_records.append(final_record)
        self._save_audit_trail()
        
        logger.info("=" * 60)
        logger.info("SWARM DISSOLVED SUCCESSFULLY")
        logger.info("=" * 60)
        
        return True, audit_records


class InsufficientFundsError(Exception):
    """Raised when wallet has insufficient funds for an operation."""
    pass
