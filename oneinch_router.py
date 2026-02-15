#!/usr/bin/env python3
"""
1inch Aggregator Integration
============================
Uses 1inch API for best swap routing across all DEXs on Base.

Benefits:
- Aggregates liquidity from all DEXs (V4, V3, V2, Aerodrome, etc.)
- Finds best price automatically
- Handles complex routing
- 0.5% fee (typically)

1inch on Base:
- Chain ID: 8453
- Router: 0x1111111254eeb25477b68fb85ed929f73a960582
- API: https://api.1inch.dev/swap/v5.2/8453/
"""

import requests
from typing import Optional, Tuple, Dict, Any
from decimal import Decimal
from web3 import Web3
from eth_account import Account

# 1inch Router on Base
ONEINCH_ROUTER = "0x1111111254eeb25477b68fb85ed929f73a960582"

# 1inch Router ABI (simplified - key functions)
ONEINCH_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "caller", "type": "address"},
            {"internalType": "address", "name": "srcToken", "type": "address"},
            {"internalType": "address", "name": "dstToken", "type": "address"},
            {"internalType": "address", "name": "srcReceiver", "type": "address"},
            {"internalType": "address", "name": "dstReceiver", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "uint256", "name": "minReturn", "type": "uint256"},
            {"internalType": "uint256", "name": "flags", "type": "uint256"},
            {"internalType": "bytes", "name": "permit", "type": "bytes"},
            {"internalType": "bytes", "name": "data", "type": "bytes"}
        ],
        "name": "swap",
        "outputs": [
            {"internalType": "uint256", "name": "returnAmount", "type": "uint256"},
            {"internalType": "uint256", "name": "spentAmount", "type": "uint256"}
        ],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "contract IAggregationExecutor", "name": "caller", "type": "address"},
            {"components": [
                {"internalType": "address", "name": "srcToken", "type": "address"},
                {"internalType": "address", "name": "dstToken", "type": "address"},
                {"internalType": "address", "name": "srcReceiver", "type": "address"},
                {"internalType": "address", "name": "dstReceiver", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"},
                {"internalType": "uint256", "name": "minReturnAmount", "type": "uint256"},
                {"internalType": "uint256", "name": "flags", "type": "uint256"}
            ], "internalType": "struct SwapDescription", "name": "desc", "type": "tuple"},
            {"internalType": "bytes", "name": "data", "type": "bytes"},
            {"internalType": "bytes", "name": "permit", "type": "bytes"}
        ],
        "name": "swap",
        "outputs": [
            {"internalType": "uint256", "name": "returnAmount", "type": "uint256"},
            {"internalType": "uint256", "name": "spentAmount", "type": "uint256"}
        ],
        "stateMutability": "payable",
        "type": "function"
    }
]

# ERC20 ABI
ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
]


class OneInchAggregator:
    """
    1inch aggregator for best swap routing on Base.
    
    Uses 1inch API to get optimal swap data and executes via router contract.
    """
    
    def __init__(self, w3: Web3, account: Account, api_key: Optional[str] = None):
        """
        Initialize 1inch aggregator.
        
        Args:
            w3: Web3 instance
            account: Account for signing
            api_key: Optional 1inch API key (can work without for basic swaps)
        """
        self.w3 = w3
        self.account = account
        self.api_key = api_key
        self.chain_id = 8453  # Base
        
        # Initialize router contract
        self.router = w3.eth.contract(
            address=w3.to_checksum_address(ONEINCH_ROUTER),
            abi=ONEINCH_ROUTER_ABI
        )
        
        self.api_base = f"https://api.1inch.dev/swap/v5.2/{self.chain_id}"
    
    def _get_swap_data(self, from_token: str, to_token: str, amount: int, slippage: float = 1.0) -> Optional[Dict]:
        """
        Get swap data from 1inch API.
        
        Args:
            from_token: Source token address
            to_token: Destination token address
            amount: Amount in wei
            slippage: Max slippage %
            
        Returns:
            Swap data dict or None if error
        """
        try:
            params = {
                "src": from_token,
                "dst": to_token,
                "amount": str(amount),
                "from": self.account.address,
                "slippage": slippage,
                "disableEstimate": "false",
                "allowPartialFill": "false",
            }
            
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            response = requests.get(
                f"{self.api_base}/swap",
                params=params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[dim]1inch API error: {response.status_code} - {response.text[:100]}[/dim]")
                return None
                
        except Exception as e:
            print(f"[dim]1inch API request failed: {e}[/dim]")
            return None
    
    def swap_eth_for_tokens(self, token_address: str, amount_eth: Decimal, slippage_percent: float = 1.0) -> Tuple[bool, str]:
        """
        Swap ETH for tokens via 1inch.
        
        Args:
            token_address: Token to buy
            amount_eth: Amount of ETH to swap
            slippage_percent: Max slippage
            
        Returns:
            (success, tx_hash or error)
        """
        try:
            weth = "0x4200000000000000000000000000000000000006"
            amount_wei = int(amount_eth * 10**18)
            
            print(f"[dim]Getting 1inch quote for {amount_eth} ETH -> Token...[/dim]")
            
            # Get swap data from 1inch API
            swap_data = self._get_swap_data(weth, token_address, amount_wei, slippage_percent)
            
            if not swap_data:
                return False, "Failed to get swap data from 1inch API"
            
            # Extract transaction data
            tx_data = swap_data.get("tx", {})
            
            # Build transaction
            tx = {
                'to': self.w3.to_checksum_address(tx_data.get("to", ONEINCH_ROUTER)),
                'data': tx_data.get("data"),
                'value': amount_wei,  # ETH amount
                'gas': int(tx_data.get("gas", 300000)),
                'gasPrice': int(tx_data.get("gasPrice", self.w3.eth.gas_price)),
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': self.chain_id,
            }
            
            print(f"[dim]Executing 1inch swap...[/dim]")
            
            # Sign and send
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            print(f"[dim]TX: {self.w3.to_hex(tx_hash)}[/dim]")
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                return True, self.w3.to_hex(tx_hash)
            else:
                return False, f"Transaction failed (status={receipt['status']})"
                
        except Exception as e:
            return False, f"1inch swap error: {e}"
    
    def swap_tokens_for_eth(self, token_address: str, amount_tokens: Decimal, token_decimals: int = 18, slippage_percent: float = 1.0) -> Tuple[bool, str]:
        """
        Swap tokens for ETH via 1inch.
        
        Args:
            token_address: Token to sell
            amount_tokens: Amount of tokens to swap
            token_decimals: Token decimals
            slippage_percent: Max slippage
            
        Returns:
            (success, tx_hash or error)
        """
        try:
            weth = "0x4200000000000000000000000000000000000006"
            amount_units = int(amount_tokens * (10 ** token_decimals))
            
            print(f"[dim]Getting 1inch quote for Token -> ETH...[/dim]")
            
            # First approve 1inch router to spend tokens
            token_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            
            approve_tx = token_contract.functions.approve(
                ONEINCH_ROUTER,
                amount_units
            ).build_transaction({
                'from': self.account.address,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': self.chain_id,
            })
            
            signed_approve = self.account.sign_transaction(approve_tx)
            approve_hash = self.w3.eth.send_raw_transaction(signed_approve.raw_transaction)
            self.w3.eth.wait_for_transaction_receipt(approve_hash, timeout=120)
            print(f"[dim]Approved 1inch to spend tokens[/dim]")
            
            # Get swap data from 1inch API
            swap_data = self._get_swap_data(token_address, weth, amount_units, slippage_percent)
            
            if not swap_data:
                return False, "Failed to get swap data from 1inch API"
            
            # Extract transaction data
            tx_data = swap_data.get("tx", {})
            
            # Build transaction
            tx = {
                'to': self.w3.to_checksum_address(tx_data.get("to", ONEINCH_ROUTER)),
                'data': tx_data.get("data"),
                'value': 0,  # No ETH sent for token->ETH
                'gas': int(tx_data.get("gas", 300000)),
                'gasPrice': int(tx_data.get("gasPrice", self.w3.eth.gas_price)),
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': self.chain_id,
            }
            
            print(f"[dim]Executing 1inch swap...[/dim]")
            
            # Sign and send
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            print(f"[dim]TX: {self.w3.to_hex(tx_hash)}[/dim]")
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                return True, self.w3.to_hex(tx_hash)
            else:
                return False, f"Transaction failed (status={receipt['status']})"
                
        except Exception as e:
            return False, f"1inch swap error: {e}"
