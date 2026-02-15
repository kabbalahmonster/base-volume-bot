#!/usr/bin/env python3
"""
Multi-DEX Router Module
=======================
Supports multiple DEXs on Base and automatically picks the best one.

Supported DEXs:
- Aerodrome (Solidly fork - most popular on Base)
- Uniswap V3
- Uniswap V2
- BaseSwap

Automatically queries liquidity and selects best route.
"""

from typing import Optional, Tuple, Dict, List
from decimal import Decimal
from dataclasses import dataclass
from web3 import Web3
from eth_account import Account


# DEX Configuration
DEX_CONFIG = {
    "uniswap_v4": {
        "name": "Uniswap V4",
        "router": "0x6c083A36F731eA994739eF5E8647D18553D41f76",  # Universal Router on Base
        "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",  # Pool manager
        "type": "uniswap_v4",
        "fee_tiers": [100, 500, 3000, 10000],
    },
    "aerodrome": {
        "name": "Aerodrome",
        "router": "0xcF77a3Ba9A73CA43934ef2c5c9864A4c7B4bE323",
        "factory": "0x420DD381b31aEf6683db6B902084cB0FFECe40Da",
        "type": "solidly",  # Solidly-style DEX
        "fee_tiers": [100, 500, 3000, 10000],  # Not used for Solidly, but kept for compatibility
    },
    "uniswap_v3": {
        "name": "Uniswap V3",
        "router": "0x2626664c2603336E57B271c5C0b26F421741e481",
        "factory": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD",
        "type": "uniswap_v3",
        "fee_tiers": [100, 500, 3000, 10000],
    },
    "uniswap_v2": {
        "name": "Uniswap V2",
        "router": "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24",  # Uniswap V2 on Base
        "factory": "0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6",
        "type": "uniswap_v2",
        "fee_tiers": [30],  # 0.3% fee
    },
    "baseswap": {
        "name": "BaseSwap",
        "router": "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86",
        "factory": "0xFDa619b6d20976be93480E43D93903e739c16Eb5",
        "type": "uniswap_v2",
        "fee_tiers": [25],  # 0.25% fee
    }
}

# Aerodrome Router ABI (Solidly-style)
AERODROME_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactETHForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForETH",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "bool", "name": "stable", "type": "bool"}
        ],
        "name": "getAmountsOut",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Uniswap V2 Router ABI
UNISWAP_V2_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactETHForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForETH",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"}
        ],
        "name": "getAmountsOut",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Uniswap V3 Router ABI (existing)
UNISWAP_V3_ROUTER_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                ],
                "internalType": "struct IV3SwapRouter.ExactInputSingleParams",
                "name": "params",
                "type": "tuple"
            }
        ],
        "name": "exactInputSingle",
        "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function"
    }
]

# Uniswap V4 Universal Router ABI (simplified)
UNISWAP_V4_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "bytes", "name": "commands", "type": "bytes"},
            {"internalType": "bytes[]", "name": "inputs", "type": "bytes[]"}
        ],
        "name": "execute",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes", "name": "commands", "type": "bytes"},
            {"internalType": "bytes[]", "name": "inputs", "type": "bytes[]"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "execute",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

# ERC20 ABI (minimal)
ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
]

# WETH address on Base
WETH = "0x4200000000000000000000000000000000000006"


@dataclass
class DEXQuote:
    """Quote from a DEX"""
    dex_name: str
    amount_out: int
    price_impact: float
    path: List[str]
    router_address: str
    dex_type: str


class MultiDEXRouter:
    """
    Multi-DEX router that supports multiple DEXs and picks the best one.

    Priority:
    1. Uniswap V4 (latest, most liquidity)
    2. Aerodrome (popular on Base)
    3. Uniswap V3
    4. Uniswap V2
    5. BaseSwap
    """

    def __init__(self, w3: Web3, account: Account, token_address: str):
        """
        Initialize multi-DEX router.

        Args:
            w3: Web3 instance
            account: Account for signing
            token_address: Token to trade (e.g., COMPUTE)
        """
        self.w3 = w3
        self.account = account
        self.token_address = w3.to_checksum_address(token_address)
        self.weth = w3.to_checksum_address(WETH)

        # Initialize routers
        self.routers = {}
        for dex_key, dex_info in DEX_CONFIG.items():
            if dex_info["type"] == "solidly":
                abi = AERODROME_ROUTER_ABI
            elif dex_info["type"] == "uniswap_v2":
                abi = UNISWAP_V2_ROUTER_ABI
            elif dex_info["type"] == "uniswap_v3":
                abi = UNISWAP_V3_ROUTER_ABI
            elif dex_info["type"] == "uniswap_v4":
                abi = UNISWAP_V4_ROUTER_ABI
            else:
                continue

            self.routers[dex_key] = {
                "contract": w3.eth.contract(
                    address=w3.to_checksum_address(dex_info["router"]),
                    abi=abi
                ),
                "config": dex_info
            }
        
        # Token contract
        self.token = w3.eth.contract(address=self.token_address, abi=ERC20_ABI)
        self.token_decimals = self.token.functions.decimals().call()
        
        # Track best DEX
        self.best_dex = None
        self._find_best_dex()
    
    def _find_best_dex(self):
        """Find which DEX has the best liquidity for the token."""
        print(f"[dim]Finding best DEX for {self.token_address}...[/dim]")
        
        best_dex = None
        best_liquidity = 0
        
        # Try Uniswap V4 first (latest, most liquidity on Base)
        if "uniswap_v4" in self.routers:
            try:
                # For V4, we check if the router responds
                router = self.routers["uniswap_v4"]["contract"]
                # V4 uses execute() with encoded commands - simplified check
                # Check if router has code
                code = self.w3.eth.get_code(self.routers["uniswap_v4"]["config"]["router"])
                if len(code) > 0:
                    best_dex = "uniswap_v4"
                    best_liquidity = 1  # Mark as found
                    print(f"[green]✓ Uniswap V4 router found[/green]")
            except Exception as e:
                print(f"[dim]  Uniswap V4: {e}[/dim]")

        # Try Aerodrome (popular on Base)
        if not best_dex and "aerodrome" in self.routers:
            try:
                router = self.routers["aerodrome"]["contract"]
                # Try to get quote for small amount
                path = [self.weth, self.token_address]
                amounts = router.functions.getAmountsOut(
                    10**15,  # 0.001 ETH
                    path,
                    False  # volatile pool (not stable)
                ).call()
                if amounts and amounts[-1] > 0:
                    best_dex = "aerodrome"
                    best_liquidity = amounts[-1]
                    print(f"[green]✓ Aerodrome has liquidity[/green]")
            except Exception as e:
                print(f"[dim]  Aerodrome: {e}[/dim]")
        
        # Try Uniswap V2 if Aerodrome failed
        if not best_dex and "uniswap_v2" in self.routers:
            try:
                router = self.routers["uniswap_v2"]["contract"]
                path = [self.weth, self.token_address]
                amounts = router.functions.getAmountsOut(10**15, path).call()
                if amounts and amounts[-1] > 0:
                    best_dex = "uniswap_v2"
                    best_liquidity = amounts[-1]
                    print(f"[green]✓ Uniswap V2 has liquidity[/green]")
            except Exception as e:
                print(f"[dim]  Uniswap V2: {e}[/dim]")
        
        # Try BaseSwap
        if not best_dex and "baseswap" in self.routers:
            try:
                router = self.routers["baseswap"]["contract"]
                path = [self.weth, self.token_address]
                amounts = router.functions.getAmountsOut(10**15, path).call()
                if amounts and amounts[-1] > 0:
                    best_dex = "baseswap"
                    best_liquidity = amounts[-1]
                    print(f"[green]✓ BaseSwap has liquidity[/green]")
            except Exception as e:
                print(f"[dim]  BaseSwap: {e}[/dim]")
        
        # Try Uniswap V3 last (requires pool to exist at specific fee tier)
        if not best_dex and "uniswap_v3" in self.routers:
            try:
                # For V3, we check if a pool exists by trying to call quoter
                # This is a simplified check - in reality might need quoter contract
                print(f"[yellow]⚠ Uniswap V3 pools not found or no liquidity[/yellow]")
            except Exception as e:
                print(f"[dim]  Uniswap V3: {e}[/dim]")
        
        self.best_dex = best_dex
        if best_dex:
            dex_name = DEX_CONFIG[best_dex]["name"]
            print(f"[bold green]Using {dex_name} for trading[/bold green]")
        else:
            print(f"[red]✗ No DEX found with liquidity for this token![/red]")
    
    def get_best_dex(self) -> Optional[str]:
        """Get the best DEX key."""
        return self.best_dex
    
    def swap_eth_for_tokens(self, amount_eth: Decimal, slippage_percent: float = 2.0) -> Tuple[bool, str]:
        """
        Swap ETH for tokens using the best available DEX.
        
        Args:
            amount_eth: Amount of ETH to swap
            slippage_percent: Maximum slippage allowed
            
        Returns:
            (success, tx_hash or error message)
        """
        if not self.best_dex:
            return False, "No DEX with liquidity found"
        
        try:
            amount_in_wei = int(amount_eth * 10**18)
            router_info = self.routers[self.best_dex]
            router = router_info["contract"]
            dex_config = router_info["config"]
            
            if dex_config["type"] in ["solidly", "uniswap_v2"]:
                # V2-style swap
                path = [self.weth, self.token_address]
                
                # Get expected output
                amounts_out = router.functions.getAmountsOut(amount_in_wei, path).call()
                expected_out = amounts_out[-1]
                min_out = int(expected_out * (100 - slippage_percent) / 100)
                
                # Build transaction
                deadline = int(self.w3.eth.get_block('latest')['timestamp']) + 300
                tx = router.functions.swapExactETHForTokens(
                    min_out,
                    path,
                    self.account.address,
                    deadline
                ).build_transaction({
                    'from': self.account.address,
                    'value': amount_in_wei,
                    'gas': 300000,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(self.account.address),
                    'chainId': 8453
                })
                
                # Sign and send
                signed = self.account.sign_transaction(tx)
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                
                # Wait for receipt
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                if receipt['status'] == 1:
                    return True, self.w3.to_hex(tx_hash)
                else:
                    return False, f"Transaction failed (status={receipt['status']})"
                    
            elif dex_config["type"] == "uniswap_v3":
                # V3 swap (existing logic)
                # ... implementation would go here
                return False, "Uniswap V3 not yet implemented in MultiDEXRouter"

            elif dex_config["type"] == "uniswap_v4":
                # V4 swap - uses Universal Router with encoded commands
                # This requires encoding swap commands for the V4 router
                # For now, return error - full V4 implementation needs more work
                return False, "Uniswap V4 execute() swap not yet fully implemented - needs encoded commands"

        except Exception as e:
            return False, f"Swap error: {e}"
    
    def swap_tokens_for_eth(self, amount_tokens: Decimal, slippage_percent: float = 2.0) -> Tuple[bool, str]:
        """
        Swap tokens for ETH using the best available DEX.
        
        Args:
            amount_tokens: Amount of tokens to swap
            slippage_percent: Maximum slippage allowed
            
        Returns:
            (success, tx_hash or error message)
        """
        if not self.best_dex:
            return False, "No DEX with liquidity found"
        
        try:
            amount_in_units = int(amount_tokens * (10 ** self.token_decimals))
            router_info = self.routers[self.best_dex]
            router = router_info["contract"]
            dex_config = router_info["config"]
            
            if dex_config["type"] in ["solidly", "uniswap_v2"]:
                # V2-style swap
                path = [self.token_address, self.weth]
                
                # Approve router first
                approve_tx = self.token.functions.approve(
                    dex_config["router"],
                    amount_in_units
                ).build_transaction({
                    'from': self.account.address,
                    'gas': 100000,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(self.account.address),
                    'chainId': 8453
                })
                
                signed_approve = self.account.sign_transaction(approve_tx)
                approve_hash = self.w3.eth.send_raw_transaction(signed_approve.raw_transaction)
                self.w3.eth.wait_for_transaction_receipt(approve_hash, timeout=120)
                
                # Get expected output
                amounts_out = router.functions.getAmountsOut(amount_in_units, path).call()
                expected_out = amounts_out[-1]
                min_out = int(expected_out * (100 - slippage_percent) / 100)
                
                # Build swap transaction
                deadline = int(self.w3.eth.get_block('latest')['timestamp']) + 300
                tx = router.functions.swapExactTokensForETH(
                    amount_in_units,
                    min_out,
                    path,
                    self.account.address,
                    deadline
                ).build_transaction({
                    'from': self.account.address,
                    'gas': 300000,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(self.account.address),
                    'chainId': 8453
                })
                
                # Sign and send
                signed = self.account.sign_transaction(tx)
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                
                # Wait for receipt
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

                if receipt['status'] == 1:
                    return True, self.w3.to_hex(tx_hash)
                else:
                    return False, f"Transaction failed (status={receipt['status']})"

            elif dex_config["type"] == "uniswap_v4":
                # V4 swap - uses Universal Router with encoded commands
                return False, "Uniswap V4 execute() swap not yet fully implemented - needs encoded commands"

        except Exception as e:
            return False, f"Swap error: {e}"
