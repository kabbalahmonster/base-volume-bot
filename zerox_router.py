#!/usr/bin/env python3
"""
0x Aggregator Integration v2
============================
Uses 0x API v2 Permit2 for best swap routing on Base.

API Docs: https://0x.org/docs/0x-swap-api/guides/swap-tokens-with-0x-swap-api-permit2
"""

import requests
from typing import Optional, Tuple, Dict, Any
from decimal import Decimal
from web3 import Web3
from eth_account import Account

ZEROX_API_BASE = "https://api.0x.org"
ZEROX_CHAIN_ID = 8453

# WETH on Base
WETH_BASE = "0x4200000000000000000000000000000000000006"

ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
]


class ZeroXAggregator:
    """0x aggregator v2 for best swap routing on Base."""
    
    def __init__(self, w3: Web3, account: Account, api_key: Optional[str] = None):
        self.w3 = w3
        self.account = account
        self.api_key = api_key
        self.chain_id = ZEROX_CHAIN_ID
        
        # v2 API requires version header
        self.headers = {
            "Accept": "application/json",
            "0x-version": "v2"
        }
        if api_key:
            self.headers["0x-api-key"] = api_key
    
    def _get_permit2_quote(self, sell_token: str, buy_token: str, sell_amount: int,
                           slippage: float = 1.0) -> Optional[Dict]:
        """Get swap quote from 0x v2 Permit2 API."""
        try:
            params = {
                "chainId": self.chain_id,
                "sellToken": sell_token,
                "buyToken": buy_token,
                "sellAmount": str(sell_amount),
                "slippageBps": str(int(slippage * 100)),  # v2 uses basis points
                "taker": self.account.address,  # v2 uses 'taker' not 'takerAddress'
            }
            
            print(f"[dim]Calling 0x v2 Permit2 API...[/dim]")
            
            response = requests.get(
                f"{ZEROX_API_BASE}/swap/permit2/quote",
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_text = response.text[:300] if response.text else "Unknown error"
                print(f"[yellow]0x API error: {response.status_code} - {error_text}[/yellow]")
                return None
                
        except Exception as e:
            print(f"[yellow]0x API request failed: {e}[/yellow]")
            return None
    
    def swap_eth_for_tokens(self, token_address: str, amount_eth: Decimal,
                           slippage_percent: float = 1.0) -> Tuple[bool, str]:
        """Swap ETH for tokens via 0x v2 Permit2.
        
        Note: 0x v2 uses WETH for ETH swaps (not ETH placeholder).
        We need to wrap ETH first, then use Permit2 for the swap.
        """
        try:
            amount_wei = int(amount_eth * 10**18)
            
            print(f"[dim]Getting 0x v2 quote for {amount_eth} WETH -> Token...[/dim]")
            
            # v2 uses actual WETH address, not ETH placeholder
            quote = self._get_permit2_quote(
                WETH_BASE,  # Use WETH, not ETH placeholder
                token_address,
                amount_wei,
                slippage_percent
            )
            
            if not quote:
                # Try with ETH placeholder as fallback
                print(f"[dim]Retrying with ETH placeholder...[/dim]")
                quote = self._get_permit2_quote(
                    "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                    token_address,
                    amount_wei,
                    slippage_percent
                )
                if not quote:
                    return False, "Failed to get quote from 0x API"
            
            print(f"[green]✓ 0x route found![/green]")
            print(f"[dim]  Expected output: {quote.get('buyAmount', 'N/A')}[/dim]")
            print(f"[dim]  Liquidity available: {quote.get('liquidityAvailable', False)}[/dim]")
            
            # Check if there are any issues
            issues = quote.get('issues', {})
            if issues:
                print(f"[yellow]  Issues: {issues}[/yellow]")
            
            # Get transaction data
            transaction = quote.get('transaction', {})
            if not transaction:
                return False, "No transaction data in quote"
            
            # Build transaction
            tx = {
                'to': self.w3.to_checksum_address(transaction["to"]),
                'data': transaction["data"],
                'value': int(transaction.get("value", 0)),
                'gas': int(transaction.get("gas", 150000)),
                'gasPrice': int(transaction.get("gasPrice", self.w3.eth.gas_price)),
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': self.chain_id,
            }
            
            print(f"[dim]Executing 0x swap...[/dim]")
            
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hex = self.w3.to_hex(tx_hash)
            
            print(f"[dim]TX: {tx_hex}[/dim]")
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                print(f"[green]✓ 0x swap successful! Gas: {receipt['gasUsed']}[/green]")
                return True, tx_hex
            else:
                return False, f"Transaction failed (status={receipt['status']})"
                
        except Exception as e:
            import traceback
            print(f"[red]0x swap error: {e}[/red]")
            print(f"[dim]{traceback.format_exc()[:300]}...[/dim]")
            return False, f"0x swap error: {e}"
    
    def swap_tokens_for_eth(self, token_address: str, amount_tokens: Decimal,
                           token_decimals: int = 18, slippage_percent: float = 1.0) -> Tuple[bool, str]:
        """Swap tokens for ETH via 0x v2 Permit2."""
        try:
            amount_units = int(amount_tokens * (10 ** token_decimals))
            
            print(f"[dim]Getting 0x v2 quote for Token -> WETH...[/dim]")
            
            quote = self._get_permit2_quote(
                token_address,
                WETH_BASE,  # Get WETH, user can unwrap if needed
                amount_units,
                slippage_percent
            )
            
            if not quote:
                # Try for ETH placeholder
                print(f"[dim]Retrying with ETH placeholder...[/dim]")
                quote = self._get_permit2_quote(
                    token_address,
                    "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                    amount_units,
                    slippage_percent
                )
                if not quote:
                    return False, "Failed to get quote from 0x API"
            
            print(f"[green]✓ 0x route found![/green]")
            
            # Get transaction data
            transaction = quote.get('transaction', {})
            if not transaction:
                return False, "No transaction data in quote"
            
            tx = {
                'to': self.w3.to_checksum_address(transaction["to"]),
                'data': transaction["data"],
                'value': int(transaction.get("value", 0)),
                'gas': int(transaction.get("gas", 150000)),
                'gasPrice': int(transaction.get("gasPrice", self.w3.eth.gas_price)),
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': self.chain_id,
            }
            
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hex = self.w3.to_hex(tx_hash)
            
            print(f"[dim]TX: {tx_hex}[/dim]")
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                print(f"[green]✓ 0x swap successful! Gas: {receipt['gasUsed']}[/green]")
                return True, tx_hex
            else:
                return False, f"Transaction failed (status={receipt['status']})"
                
        except Exception as e:
            import traceback
            print(f"[red]0x swap error: {e}[/red]")
            print(f"[dim]{traceback.format_exc()[:300]}...[/dim]")
            return False, f"0x swap error: {e}"
