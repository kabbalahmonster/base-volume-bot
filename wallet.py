"""
Secure Wallet Management

Handles private key operations with secure memory handling.
Uses Web3 for all blockchain interactions.
"""

import os
from typing import Optional
from dataclasses import dataclass

from eth_account import Account
from web3 import Web3
from web3.types import TxParams, Wei

from config import Config
from utils import logger


@dataclass
class WalletInfo:
    """Wallet balance information."""
    eth_balance: float
    compute_balance: float
    nonce: int
    gas_price_gwei: float


class SecureWallet:
    """
    Secure wallet management with private key protection.
    
    Security features:
    - Private key never logged or exposed
    - Secure memory handling where possible
    - Address derived once and cached
    """
    
    def __init__(self, config: Config, password: Optional[str] = None):
        self.config = config
        self._web3 = Web3(Web3.HTTPProvider(config.rpc_url))
        
        # Validate connection
        if not self._web3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC: {config.rpc_url}")
        
        # Validate chain ID
        chain_id = self._web3.eth.chain_id
        if chain_id != config.chain_id:
            raise ValueError(
                f"Chain ID mismatch. Expected {config.chain_id}, got {chain_id}"
            )
        
        # Initialize account from private key
        if not config.encrypted_private_key:
            raise ValueError("No private key provided in configuration")
        
        self._account = Account.from_key(config.encrypted_private_key)
        self.address = self._account.address
        
        logger.info(f"Wallet initialized: {self.address}")
    
    def get_web3(self) -> Web3:
        """Get Web3 instance."""
        return self._web3
    
    def get_balance_info(self) -> WalletInfo:
        """Get current wallet balances and network info."""
        eth_balance_wei = self._web3.eth.get_balance(self.address)
        eth_balance = self._web3.from_wei(eth_balance_wei, 'ether')
        
        # Get COMPUTE token balance (ERC20)
        compute_balance = self._get_erc20_balance(self.config.compute_token)
        
        nonce = self._web3.eth.get_transaction_count(self.address)
        gas_price = self._web3.eth.gas_price
        gas_price_gwei = self._web3.from_wei(gas_price, 'gwei')
        
        return WalletInfo(
            eth_balance=float(eth_balance),
            compute_balance=compute_balance,
            nonce=nonce,
            gas_price_gwei=float(gas_price_gwei)
        )
    
    def _get_erc20_balance(self, token_address: str) -> float:
        """Get ERC20 token balance."""
        # ERC20 balanceOf function signature
        # balanceOf(address) -> 0x70a08231
        data = "0x70a08231000000000000000000000000" + self.address[2:]
        
        try:
            result = self._web3.eth.call({
                'to': token_address,
                'data': data
            })
            
            # Parse result (uint256)
            balance = int(result.hex(), 16)
            
            # Get token decimals (default to 18)
            decimals = self._get_token_decimals(token_address)
            
            return balance / (10 ** decimals)
        except Exception as e:
            logger.warning(f"Failed to get token balance: {e}")
            return 0.0
    
    def _get_token_decimals(self, token_address: str) -> int:
        """Get ERC20 token decimals."""
        # decimals() -> 0x313ce567
        try:
            result = self._web3.eth.call({
                'to': token_address,
                'data': '0x313ce567'
            })
            return int(result.hex(), 16)
        except:
            return 18  # Default to 18 decimals
    
    def get_erc20_balance_raw(self, token_address: str) -> int:
        """Get raw ERC20 token balance (wei units)."""
        data = "0x70a08231000000000000000000000000" + self.address[2:]
        
        try:
            result = self._web3.eth.call({
                'to': token_address,
                'data': data
            })
            return int(result.hex(), 16)
        except Exception as e:
            logger.warning(f"Failed to get raw token balance: {e}")
            return 0
    
    def sign_transaction(self, tx_dict: TxParams) -> dict:
        """Sign a transaction with the private key."""
        signed_tx = self._account.sign_transaction(tx_dict)
        return signed_tx
    
    def send_raw_transaction(self, signed_tx: dict) -> str:
        """Send a signed raw transaction."""
        tx_hash = self._web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash.hex()
    
    def wait_for_transaction(self, tx_hash: str, timeout: int = 120) -> dict:
        """Wait for transaction receipt."""
        receipt = self._web3.eth.wait_for_transaction_receipt(
            tx_hash,
            timeout=timeout
        )
        return receipt
    
    def estimate_gas(self, tx_dict: TxParams) -> int:
        """Estimate gas for a transaction."""
        try:
            gas = self._web3.eth.estimate_gas(tx_dict)
            return int(gas * self.config.gas_limit_buffer)
        except Exception as e:
            logger.warning(f"Gas estimation failed: {e}")
            # Return default gas limit
            return 300000
    
    def get_nonce(self) -> int:
        """Get current transaction nonce."""
        return self._web3.eth.get_transaction_count(self.address)
    
    def is_contract(self, address: str) -> bool:
        """Check if address is a contract."""
        code = self._web3.eth.get_code(address)
        return len(code) > 0
    
    def validate_address(self, address: str) -> bool:
        """Validate Ethereum address format."""
        return self._web3.is_address(address)
    
    def checksum_address(self, address: str) -> str:
        """Convert address to checksum format."""
        return self._web3.to_checksum_address(address)
