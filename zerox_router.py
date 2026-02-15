#!/usr/bin/env python3
"""
0x Aggregator Integration
=========================
Uses 0x API for best swap routing across all DEXs on Base.

Benefits:
- Aggregates liquidity from all DEXs (V4, V3, V2, etc.)
- Finds best price automatically
- No KYC required for basic tier
- Lower latency than 1inch

0x on Base:
- Chain ID: 8453
- API: https://api.0x.org/
- Docs: https://0x.org/docs/api

Note: This is the 0x implementation branch.
For 1inch, see feature/1inch-aggregator branch.
"""

import requests
from typing import Optional, Tuple, Dict, Any
from decimal import Decimal
from web3 import Web3
from eth_account import Account

# 0x API Configuration
ZEROX_API_BASE = "https://api.0x.org"
ZEROX_CHAIN_ID = 8453  # Base

# 0x Exchange Proxy on Base (for approvals)
ZEROX_EXCHANGE_PROXY = "0xdef1c0ded9bec7f1a1670819833240f027b25eff"

# ERC20 ABI
ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
]


class ZeroXAggregator:
    """
    0x aggregator for best swap routing on Base.
    
    Uses 0x API to get optimal swap data and executes via transaction.
    """
    
    def __init__(self, w3: Web3, account: Account, api_key: Optional[str] = None):
        """
        Initialize 0x aggregator.
        
        Args:
            w3: Web3 instance
            account: Account for signing
            api_key: 0x API key (optional, increases rate limits)
        """
        self.w3 = w3
        self.account = account
        self.api_key = api_key
        self.chain_id = ZEROX_CHAIN_ID
        
        # API headers
        self.headers = {
            "Accept": "application/json",
        }
        if api_key:
            self.headers["0x-api-key"] = api_key
    
    def _get_quote(self, sell_token: str, buy_token: str, sell_amount: int, 
                   slippage: float = 1.0, taker_address: Optional[str] = None) -> Optional[Dict]:
        """
        Get swap quote from 0x API.
        
        Args:
            sell_token: Token to sell (address)
            buy_token: Token to buy (address)
            sell_amount: Amount to sell (in wei/token units)
            slippage: Max slippage %
            taker_address: Address that will execute the swap
            
        Returns:
            Quote data dict or None if error
        """
        try:
            params = {
                "chainId": self.chain_id,
                "sellToken": sell_token,
                "buyToken": buy_token,
                "sellAmount": str(sell_amount),
                "slippagePercentage": str(slippage / 100),  # 0x uses 0.01 for 1%
            }
            
            if taker_address:
                params["takerAddress"] = taker_address
            
            response = requests.get(
                f"{ZEROX_API_BASE}/swap/v1/quote",
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[dim]0x API error: {response.status_code} - {response.text[:200]}[/dim]")
                return None
                
        except Exception as e:
            print(f"[dim]0x API request failed: {e}[/dim]")
            return None
    
    def swap_eth_for_tokens(self, token_address: str, amount_eth: Decimal, 
                           slippage_percent: float = 1.0) -> Tuple[bool, str]:
        """
        Swap ETH for tokens via 0x.
        
        Args:
            token_address: Token to buy
            amount_eth: Amount of ETH to swap
            slippage_percent: Max slippage
            
        Returns:
            (success, tx_hash or error)
        """
        try:
            # 0x uses special address for ETH
            eth_address = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
            amount_wei = int(amount_eth * 10**18)
            
            print(f"[dim]Getting 0x quote for {amount_eth} ETH -> Token...[/dim]")
            
            # Get quote from 0x API
            quote = self._get_quote(
                eth_address,
                token_address,
                amount_wei,
                slippage_percent,
                self.account.address
            )
            
            if not quote:
                return False, "Failed to get quote from 0x API"
            
            print(f"[dim]0x route found: {quote.get('data', 'N/A')[:50]}...[/dim]")
            
            # Build transaction from quote
            tx = {
                'to': self.w3.to_checksum_address(quote["to"]),
                'data': quote["data"],
                'value': int(quote["value"]),  # ETH amount
                'gas': int(quote["gas"]),
                'gasPrice': int(quote["gasPrice"]),
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': self.chain_id,
            }
            
            print(f"[dim]Executing 0x swap...[/dim]")
            
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
            return False, f"0x swap error: {e}"
    
    def swap_tokens_for_eth(self, token_address: str, amount_tokens: Decimal,
                           token_decimals: int = 18, slippage_percent: float = 1.0) -> Tuple[bool, str]:
        """
        Swap tokens for ETH via 0x.
        
        Args:
            token_address: Token to sell
            amount_tokens: Amount of tokens to swap
            token_decimals: Token decimals
            slippage_percent: Max slippage
            
        Returns:
            (success, tx_hash or error)
        """
        try:
            eth_address = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
            amount_units = int(amount_tokens * (10 ** token_decimals))
            
            print(f"[dim]Getting 0x quote for Token -> ETH...[/dim]")
            
            # First approve 0x exchange proxy to spend tokens
            token_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            
            # Check current allowance
            current_allowance = token_contract.functions.allowance(
                self.account.address,
                ZEROX_EXCHANGE_PROXY
            ).call()
            
            if current_allowance < amount_units:
                print(f"[dim]Approving 0x to spend tokens...[/dim]")
                approve_tx = token_contract.functions.approve(
                    ZEROX_EXCHANGE_PROXY,
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
                print(f"[dim]Approved 0x to spend tokens[/dim]")
            
            # Get quote from 0x API
            quote = self._get_quote(
                token_address,
                eth_address,
                amount_units,
                slippage_percent,
                self.account.address
            )
            
            if not quote:
                return False, "Failed to get quote from 0x API"
            
            print(f"[dim]0x route found: {quote.get('data', 'N/A')[:50]}...[/dim]")
            
            # Build transaction from quote
            tx = {
                'to': self.w3.to_checksum_address(quote["to"]),
                'data': quote["data"],
                'value': int(quote.get("value", 0)),  # Usually 0 for token->ETH
                'gas': int(quote["gas"]),
                'gasPrice': int(quote["gasPrice"]),
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': self.chain_id,
            }
            
            print(f"[dim]Executing 0x swap...[/dim]")
            
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
            return False, f"0x swap error: {e}"
