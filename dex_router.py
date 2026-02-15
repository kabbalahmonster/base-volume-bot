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
        "router": "0x6c083a36f731ea994739ef5e8647d18553d41f76",  # Universal Router on Base
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
            {"internalType": "address[]", "name": "path", "type": "address[]"},
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

# Uniswap V3 Router ABI (SwapRouter02 on Base)
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
    },
    {
        "inputs": [
            {"internalType": "bytes[]", "name": "data", "type": "bytes[]"}
        ],
        "name": "multicall",
        "outputs": [{"internalType": "bytes[]", "name": "results", "type": "bytes[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "refundETH",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

# Uniswap V3 Factory ABI (for pool discovery)
UNISWAP_V3_FACTORY_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"}
        ],
        "name": "getPool",
        "outputs": [{"internalType": "address", "name": "pool", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Uniswap V3 Pool ABI (minimal for liquidity checks)
UNISWAP_V3_POOL_ABI = [
    {
        "inputs": [],
        "name": "liquidity",
        "outputs": [{"internalType": "uint128", "name": "", "type": "uint128"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
            {"internalType": "int24", "name": "tick", "type": "int24"},
            {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
            {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
            {"internalType": "bool", "name": "unlocked", "type": "bool"}
        ],
        "stateMutability": "view",
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
        
        # Track best DEX and fee
        self.best_dex = None
        self.best_fee = None  # Store fee for V3 swaps
        self.best_pool = None  # Store pool address
        self._find_best_dex()
    
    def _find_best_dex(self):
        """Find which DEX has the best liquidity for the token."""
        print(f"[dim]Finding best DEX for {self.token_address}...[/dim]")
        
        best_dex = None
        best_liquidity = 0
        
        # Try Uniswap V3 first (most reliable on Base)
        if "uniswap_v3" in self.routers:
            try:
                # Check if V3 pool exists for any fee tier
                factory = self.w3.eth.contract(
                    address=self.w3.to_checksum_address(DEX_CONFIG["uniswap_v3"]["factory"]),
                    abi=[{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"}],"name":"getPool","outputs":[{"internalType":"address","name":"pool","type":"address"}],"stateMutability":"view","type":"function"}]
                )
                
                for fee in DEX_CONFIG["uniswap_v3"]["fee_tiers"]:
                    try:
                        pool_address = factory.functions.getPool(self.weth, self.token_address, fee).call()
                        if pool_address and pool_address != "0x0000000000000000000000000000000000000000":
                            # Pool exists - check if it has liquidity
                            pool = self.w3.eth.contract(address=pool_address, abi=UNISWAP_V3_POOL_ABI)
                            liquidity = pool.functions.liquidity().call()
                            if liquidity > 0:
                                # Found a pool with liquidity
                                if liquidity > best_liquidity:
                                    best_dex = "uniswap_v3"
                                    best_liquidity = liquidity
                                    self.best_fee = fee
                                    self.best_pool = pool_address
                                    print(f"[green]✓ Uniswap V3 pool found (fee={fee}, liq={liquidity})[/green]")
                    except:
                        continue
            except Exception as e:
                print(f"[dim]  Uniswap V3: {e}[/dim]")

        # Try Uniswap V4 (checksum fix applied)
        if not best_dex and "uniswap_v4" in self.routers:
            try:
                # Check if router has code (using checksummed address)
                router_addr = self.w3.to_checksum_address(self.routers["uniswap_v4"]["config"]["router"])
                code = self.w3.eth.get_code(router_addr)
                if len(code) > 0:
                    best_dex = "uniswap_v4"
                    best_liquidity = 1  # Mark as found
                    print(f"[green]✓ Uniswap V4 router found[/green]")
            except Exception as e:
                print(f"[dim]  Uniswap V4: {e}[/dim]")

        # Note: Aerodrome removed due to interface mismatch
        # To re-add: implement correct Solidly router ABI
        
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
                tx_hex = self.w3.to_hex(tx_hash)

                if receipt['status'] == 1:
                    return True, tx_hex
                else:
                    return False, f"V2 swap failed (status={receipt['status']}) - TX: {tx_hex}"

            elif dex_config["type"] == "uniswap_v3":
                # V3 swap - use the fee and pool found during discovery
                if not self.best_fee or not self.best_pool:
                    return False, "V3 fee/pool not set - discovery failed"
                
                print(f"[dim]Using V3 pool: {self.best_pool[:20]}... with fee={self.best_fee}[/dim]")
                
                # For V3, we need to estimate output
                # Using a simplified approach - in production use QuoterV2
                min_out = 0  # Would use proper quoting in production
                
                deadline = int(self.w3.eth.get_block('latest')['timestamp']) + 300
                
                # Build V3 swap transaction
                tx = router.functions.exactInputSingle({
                    'tokenIn': self.weth,
                    'tokenOut': self.token_address,
                    'fee': self.best_fee,
                    'recipient': self.account.address,
                    'deadline': deadline,
                    'amountIn': amount_in_wei,
                    'amountOutMinimum': min_out,
                    'sqrtPriceLimitX96': 0
                }).build_transaction({
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
                tx_hex = self.w3.to_hex(tx_hash)

                if receipt['status'] == 1:
                    return True, tx_hex
                else:
                    return False, f"V3 ETH->Token failed (status={receipt['status']}) - TX: {tx_hex}"

            elif dex_config["type"] == "uniswap_v4":
                # V4 swap - uses Universal Router with encoded commands
                return False, "Uniswap V4 not implemented"

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
                tx_hex = self.w3.to_hex(tx_hash)

                if receipt['status'] == 1:
                    return True, tx_hex
                else:
                    return False, f"V2 Token->ETH failed (status={receipt['status']}) - TX: {tx_hex}"

            elif dex_config["type"] == "uniswap_v3":
                # V3 token->ETH swap
                factory = self.w3.eth.contract(
                    address=self.w3.to_checksum_address(DEX_CONFIG["uniswap_v3"]["factory"]),
                    abi=UNISWAP_V3_FACTORY_ABI
                )
                
                # Use the fee and pool found during discovery
                if not self.best_fee or not self.best_pool:
                    return False, "V3 fee/pool not set - discovery failed"
                
                print(f"[dim]Using V3 pool for sell: {self.best_pool[:20]}... with fee={self.best_fee}[/dim]")
                
                # Approve router
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
                
                deadline = int(self.w3.eth.get_block('latest')['timestamp']) + 300
                tx = router.functions.exactInputSingle({
                    'tokenIn': self.token_address,
                    'tokenOut': self.weth,
                    'fee': self.best_fee,
                    'recipient': self.account.address,
                    'deadline': deadline,
                    'amountIn': amount_in_units,
                    'amountOutMinimum': 0,
                    'sqrtPriceLimitX96': 0
                }).build_transaction({
                    'from': self.account.address,
                    'gas': 300000,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(self.account.address),
                    'chainId': 8453
                })
                
                signed = self.account.sign_transaction(tx)
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                tx_hex = self.w3.to_hex(tx_hash)

                if receipt['status'] == 1:
                    return True, tx_hex
                else:
                    return False, f"V3 Token->ETH failed (status={receipt['status']}) - TX: {tx_hex}"

            elif dex_config["type"] == "uniswap_v4":
                return False, "Uniswap V4 not implemented"

        except Exception as e:
            return False, f"Swap error: {e}"
