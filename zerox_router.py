#!/usr/bin/env python3
"""
0x Aggregator Integration - Allowance Holder API
================================================
Uses 0x API v2 Allowance Holder for swaps on Base.
This is simpler than Permit2 - uses traditional token approvals.

API Docs: https://0x.org/docs/0x-swap-api/guides/swap-tokens-with-0x-swap-api
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

# ETH placeholder for 0x API
ETH_PLACEHOLDER = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"

# 0x Allowance Holder address on Base (checksummed)
ALLOWANCE_HOLDER = Web3.to_checksum_address("0x000000000022d473030f116ddee9f6b43ac78ba3")

ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
]


class ZeroXAggregator:
    """0x aggregator v2 Allowance Holder for Base."""
    
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
    
    def _get_allowance_holder_quote(self, sell_token: str, buy_token: str, sell_amount: int,
                                     slippage: float = 1.0) -> Optional[Dict]:
        """Get swap quote from 0x v2 Allowance Holder API."""
        try:
            params = {
                "chainId": self.chain_id,
                "sellToken": sell_token,
                "buyToken": buy_token,
                "sellAmount": str(sell_amount),
                "slippageBps": str(int(slippage * 100)),  # basis points
                "taker": self.account.address,
            }
            
            print(f"[dim]Calling 0x v2 Allowance Holder API...[/dim]")
            
            response = requests.get(
                f"{ZEROX_API_BASE}/swap/allowance-holder/quote",
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_text = response.text[:500] if response.text else "Unknown error"
                print(f"[yellow]0x API error: {response.status_code} - {error_text}[/yellow]")
                return None
                
        except Exception as e:
            print(f"[yellow]0x API request failed: {e}[/yellow]")
            return None
    
    def swap_eth_for_tokens(self, token_address: str, amount_eth: Decimal,
                           slippage_percent: float = 1.0) -> Tuple[bool, str]:
        """Swap ETH for tokens via 0x v2 Allowance Holder.
        
        For ETH -> Token, we just send ETH with the transaction.
        No approvals needed for the sell side (ETH is native).
        """
        try:
            amount_wei = int(amount_eth * 10**18)
            
            print(f"[dim]Getting 0x Allowance Holder quote for {amount_eth} ETH -> Token...[/dim]")
            
            # Use ETH placeholder for native ETH
            quote = self._get_allowance_holder_quote(
                ETH_PLACEHOLDER,  # Native ETH
                token_address,
                amount_wei,
                slippage_percent
            )
            
            if not quote:
                return False, "Failed to get quote from 0x API"
            
            print(f"[green]✓ 0x route found![/green]")
            print(f"[dim]  Expected output: {quote.get('buyAmount', 'N/A')}[/dim]")
            print(f"[dim]  Liquidity available: {quote.get('liquidityAvailable', False)}[/dim]")
            
            # Check for issues
            issues = quote.get('issues', {})
            if issues:
                allowance_issue = issues.get('allowance')
                if allowance_issue:
                    print(f"[dim]  Allowance required from: {allowance_issue.get('spender', 'N/A')}[/dim]")
            
            # Get transaction data
            transaction = quote.get('transaction', {})
            if not transaction:
                return False, "No transaction data in quote"
            
            # Build transaction
            tx = {
                'to': self.w3.to_checksum_address(transaction["to"]),
                'data': transaction["data"],
                'value': int(transaction.get("value", amount_wei)),  # ETH value to send
                'gas': int(transaction.get("gas", 200000)),
                'gasPrice': int(transaction.get("gasPrice", self.w3.eth.gas_price)),
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': self.chain_id,
            }
            
            print(f"[dim]Executing 0x swap (sending {amount_eth} ETH)...[/dim]")
            
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
        """Swap tokens for ETH via 0x v2 Allowance Holder.
        
        For Token -> ETH, we need to approve the specific spender returned by the quote.
        """
        try:
            amount_units = int(amount_tokens * (10 ** token_decimals))
            
            print(f"[dim]Getting 0x Allowance Holder quote for Token -> ETH...[/dim]")
            
            # Get quote FIRST to know which spender to approve
            quote = self._get_allowance_holder_quote(
                token_address,
                ETH_PLACEHOLDER,  # Native ETH
                amount_units,
                slippage_percent
            )
            
            if not quote:
                return False, "Failed to get quote from 0x API"
            
            print(f"[green]✓ 0x route found![/green]")
            
            # Get the allowance target from the quote (with fallback)
            issues = quote.get('issues') or {}
            allowance_issue = issues.get('allowance') or {}
            allowance_target = allowance_issue.get('spender') or quote.get('allowanceTarget') or ALLOWANCE_HOLDER
            
            # CRITICAL: Checksum the address for web3.py
            allowance_target = self.w3.to_checksum_address(allowance_target)
            
            print(f"[dim]  Allowance target: {allowance_target}[/dim]")
            
            # Setup token contract
            token_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            
            # Check and approve the CORRECT allowance target
            current_allowance = token_contract.functions.allowance(
                self.account.address,
                allowance_target
            ).call()
            
            if current_allowance < amount_units:
                print(f"[dim]Approving {allowance_target[:20]}... to spend tokens...[/dim]")
                
                # Use 'pending' nonce to avoid conflicts
                approve_nonce = self.w3.eth.get_transaction_count(self.account.address, 'pending')
                
                approve_tx = token_contract.functions.approve(
                    allowance_target,
                    amount_units
                ).build_transaction({
                    'from': self.account.address,
                    'gas': 100000,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': approve_nonce,
                    'chainId': self.chain_id,
                })
                
                signed_approve = self.account.sign_transaction(approve_tx)
                approve_hash = self.w3.eth.send_raw_transaction(signed_approve.raw_transaction)
                self.w3.eth.wait_for_transaction_receipt(approve_hash, timeout=120)
                print(f"[green]✓ Approved spender[/green]")
            else:
                print(f"[dim]  Sufficient allowance already granted[/dim]")
            
            # Refresh nonce after approval (use 'pending' to get next available)
            swap_nonce = self.w3.eth.get_transaction_count(self.account.address, 'pending')
            
            # Get transaction data from quote
            transaction = quote.get('transaction', {})
            if not transaction:
                return False, "No transaction data in quote"
            
            tx = {
                'to': self.w3.to_checksum_address(transaction["to"]),
                'data': transaction["data"],
                'value': int(transaction.get("value", 0)),
                'gas': int(transaction.get("gas", 200000)),
                'gasPrice': int(transaction.get("gasPrice", self.w3.eth.gas_price)),
                'nonce': swap_nonce,  # Use refreshed nonce after approval
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
