"""
Trading Logic Module

Handles all buy/sell operations on Uniswap V3.
Includes retry logic, gas optimization, and slippage protection.
"""

import time
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from web3 import Web3
from web3.types import TxParams, Wei
from eth_abi import encode
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import Config
from wallet import SecureWallet
from utils import logger, GasOptimizer, TransactionError


# Uniswap V3 Router ABI (simplified - exactInputSingle and multicall)
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
    },
    {
        "inputs": [
            {"internalType": "address", "name": "token", "type": "address"},
            {"internalType": "uint256", "name": "amountMinimum", "type": "uint256"},
            {"internalType": "address", "name": "recipient", "type": "address"}
        ],
        "name": "sweepToken",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "stateMutability": "payable",
        "type": "receive"
    }
]

# ERC20 Token ABI (minimal)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]


@dataclass
class TradeResult:
    """Result of a trade operation."""
    success: bool
    tx_hash: Optional[str] = None
    amount_in: Optional[float] = None
    amount_out: Optional[float] = None
    gas_used: Optional[int] = None
    gas_cost_eth: Optional[float] = None
    error: Optional[str] = None
    block_number: Optional[int] = None


class ComputeTrader:
    """
    Handles all trading operations for $COMPUTE token on Uniswap V3.
    """
    
    def __init__(self, config: Config, wallet: SecureWallet):
        self.config = config
        self.wallet = wallet
        self.web3 = wallet.get_web3()
        
        # Initialize contracts
        self.router = self.web3.eth.contract(
            address=self.web3.to_checksum_address(config.router_address),
            abi=UNISWAP_V3_ROUTER_ABI
        )
        
        self.compute_token = self.web3.eth.contract(
            address=self.web3.to_checksum_address(config.compute_token),
            abi=ERC20_ABI
        )
        
        self.weth = self.web3.to_checksum_address(config.weth_address)
        self.compute = self.web3.to_checksum_address(config.compute_token)
        
        # State tracking
        self.buy_count = 0
        self.recent_activity: List[Dict[str, str]] = []
        self.total_gas_spent_eth = 0.0
        self.total_trades = 0
        self.successful_trades = 0
        
        # Gas optimizer
        self.gas_optimizer = GasOptimizer(config, self.web3)
        
        # Token decimals cache
        self._decimals_cache = {}
        
        logger.info(f"Trader initialized for {config.compute_token}")
    
    def get_eth_balance(self) -> float:
        """Get ETH balance in wallet."""
        balance = self.web3.eth.get_balance(self.wallet.address)
        return float(self.web3.from_wei(balance, 'ether'))
    
    def get_compute_balance(self) -> float:
        """Get $COMPUTE token balance."""
        try:
            balance = self.compute_token.functions.balanceOf(self.wallet.address).call()
            decimals = self._get_token_decimals(self.compute)
            return balance / (10 ** decimals)
        except Exception as e:
            logger.warning(f"Failed to get COMPUTE balance: {e}")
            return 0.0
    
    def get_compute_balance_raw(self) -> int:
        """Get raw $COMPUTE token balance."""
        try:
            return self.compute_token.functions.balanceOf(self.wallet.address).call()
        except Exception as e:
            logger.warning(f"Failed to get raw COMPUTE balance: {e}")
            return 0
    
    def _get_token_decimals(self, token_address: str) -> int:
        """Cache and return token decimals."""
        if token_address not in self._decimals_cache:
            try:
                token = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
                self._decimals_cache[token_address] = token.functions.decimals().call()
            except:
                self._decimals_cache[token_address] = 18
        return self._decimals_cache[token_address]
    
    def add_activity(self, action: str, amount: str, status: str):
        """Record trading activity."""
        self.recent_activity.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "action": action,
            "amount": amount,
            "status": status
        })
        # Keep only last 50 activities
        if len(self.recent_activity) > 50:
            self.recent_activity = self.recent_activity[-50:]
    
    def _check_gas_price(self) -> bool:
        """Check if current gas price is acceptable."""
        gas_price_gwei = float(self.web3.from_wei(self.web3.eth.gas_price, 'gwei'))
        if gas_price_gwei > self.config.max_gas_price_gwei:
            logger.warning(f"Gas too high: {gas_price_gwei:.2f} > {self.config.max_gas_price_gwei}")
            return False
        return True
    
    def _build_exact_input_single_params(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        amount_out_min: int,
        recipient: Optional[str] = None
    ) -> Dict:
        """Build parameters for exactInputSingle swap."""
        if recipient is None:
            recipient = self.wallet.address
        
        return {
            'tokenIn': token_in,
            'tokenOut': token_out,
            'fee': self.config.pool_fee,
            'recipient': recipient,
            'deadline': int(time.time()) + 300,  # 5 minute deadline
            'amountIn': amount_in,
            'amountOutMinimum': amount_out_min,
            'sqrtPriceLimitX96': 0  # No price limit
        }
    
    def _calculate_min_amount_out(
        self,
        expected_amount: int,
        slippage_percent: float
    ) -> int:
        """Calculate minimum output with slippage protection."""
        slippage_factor = 1 - (slippage_percent / 100)
        return int(expected_amount * slippage_factor)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(TransactionError),
        reraise=True
    )
    async def buy(self) -> Dict[str, Any]:
        """
        Execute a buy order (ETH -> COMPUTE).
        
        Returns:
            Dict with success, tx_hash, and other trade details
        """
        if self.config.dry_run:
            logger.info("[DRY RUN] Would buy COMPUTE with ETH")
            return {"success": True, "tx_hash": "0xDRYRUN", "dry_run": True}
        
        # Check gas price
        if not self._check_gas_price():
            return {
                "success": False,
                "error": f"Gas price exceeds maximum ({self.config.max_gas_price_gwei} Gwei)"
            }
        
        try:
            # Calculate buy amount in wei
            amount_in_wei = self.web3.to_wei(self.config.buy_amount_eth, 'ether')
            
            # Get expected output (for slippage calculation)
            # In production, you'd use the quoter contract for this
            # For now, we'll use a conservative estimate
            expected_output = await self._quote_exact_input(
                self.weth,
                self.compute,
                amount_in_wei
            )
            
            if expected_output == 0:
                return {"success": False, "error": "Could not get price quote"}
            
            # Apply slippage
            amount_out_min = self._calculate_min_amount_out(
                expected_output,
                self.config.slippage_percent
            )
            
            logger.info(f"Buying {self.config.buy_amount_eth} ETH worth of COMPUTE")
            logger.info(f"Expected output: {expected_output}, Min: {amount_out_min}")
            
            # Build swap parameters
            params = self._build_exact_input_single_params(
                self.weth,
                self.compute,
                amount_in_wei,
                amount_out_min
            )
            
            # Build transaction
            tx = self.router.functions.exactInputSingle(params).build_transaction({
                'from': self.wallet.address,
                'value': amount_in_wei,
                'nonce': self.wallet.get_nonce(),
                'gas': 300000,  # Will be estimated
                'gasPrice': self.web3.eth.gas_price
            })
            
            # Estimate gas
            try:
                gas_estimate = self.web3.eth.estimate_gas(tx)
                tx['gas'] = int(gas_estimate * self.config.gas_limit_buffer)
            except Exception as e:
                logger.warning(f"Gas estimation failed: {e}, using default")
                tx['gas'] = 300000
            
            # Optimize gas price
            tx['gasPrice'] = self.gas_optimizer.get_optimal_gas_price()
            
            # Sign and send
            signed_tx = self.wallet.sign_transaction(tx)
            tx_hash = self.wallet.send_raw_transaction(signed_tx)
            
            logger.info(f"Buy transaction sent: {tx_hash}")
            
            # Wait for confirmation
            receipt = self.wallet.wait_for_transaction(tx_hash)
            
            # Update stats
            self.total_trades += 1
            gas_cost = receipt['gasUsed'] * tx['gasPrice']
            gas_cost_eth = float(self.web3.from_wei(gas_cost, 'ether'))
            self.total_gas_spent_eth += gas_cost_eth
            
            if receipt['status'] == 1:
                self.successful_trades += 1
                logger.info(f"Buy successful! Gas used: {receipt['gasUsed']}")
                return {
                    "success": True,
                    "tx_hash": tx_hash,
                    "gas_used": receipt['gasUsed'],
                    "gas_cost_eth": gas_cost_eth,
                    "block_number": receipt['blockNumber']
                }
            else:
                raise TransactionError(f"Transaction failed: {tx_hash}")
                
        except Exception as e:
            logger.exception("Buy failed")
            return {"success": False, "error": str(e)}
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(TransactionError),
        reraise=True
    )
    async def sell_all(self) -> Dict[str, Any]:
        """
        Execute a sell order (sell all COMPUTE -> ETH).
        
        Returns:
            Dict with success, tx_hash, and other trade details
        """
        if self.config.dry_run:
            logger.info("[DRY RUN] Would sell all COMPUTE for ETH")
            return {"success": True, "tx_hash": "0xDRYRUN", "dry_run": True}
        
        # Check gas price
        if not self._check_gas_price():
            return {
                "success": False,
                "error": f"Gas price exceeds maximum ({self.config.max_gas_price_gwei} Gwei)"
            }
        
        try:
            # Get balance
            balance = self.get_compute_balance_raw()
            if balance == 0:
                return {"success": False, "error": "No COMPUTE tokens to sell"}
            
            # Check and handle approvals
            await self._ensure_approval(self.compute, self.config.router_address, balance)
            
            # Get expected ETH output
            expected_output = await self._quote_exact_input(
                self.compute,
                self.weth,
                balance
            )
            
            if expected_output == 0:
                return {"success": False, "error": "Could not get price quote"}
            
            # Apply slippage
            amount_out_min = self._calculate_min_amount_out(
                expected_output,
                self.config.slippage_percent
            )
            
            logger.info(f"Selling {balance} COMPUTE tokens")
            
            # Build swap parameters
            params = self._build_exact_input_single_params(
                self.compute,
                self.weth,
                balance,
                amount_out_min
            )
            
            # For selling tokens, we need to unwrap WETH to ETH
            # This requires a multicall: swap + unwrap
            swap_data = self.router.encodeABI(
                fn_name='exactInputSingle',
                args=[params]
            )
            
            unwrap_data = self.router.encodeABI(
                fn_name='unwrapWETH9',
                args=[amount_out_min, self.wallet.address]
            )
            
            # Build multicall transaction
            tx = self.router.functions.multicall([swap_data, unwrap_data]).build_transaction({
                'from': self.wallet.address,
                'nonce': self.wallet.get_nonce(),
                'gas': 400000,
                'gasPrice': self.web3.eth.gas_price
            })
            
            # Estimate gas
            try:
                gas_estimate = self.web3.eth.estimate_gas(tx)
                tx['gas'] = int(gas_estimate * self.config.gas_limit_buffer)
            except Exception as e:
                logger.warning(f"Gas estimation failed: {e}, using default")
            
            # Optimize gas price
            tx['gasPrice'] = self.gas_optimizer.get_optimal_gas_price()
            
            # Sign and send
            signed_tx = self.wallet.sign_transaction(tx)
            tx_hash = self.wallet.send_raw_transaction(signed_tx)
            
            logger.info(f"Sell transaction sent: {tx_hash}")
            
            # Wait for confirmation
            receipt = self.wallet.wait_for_transaction(tx_hash)
            
            # Update stats
            self.total_trades += 1
            gas_cost = receipt['gasUsed'] * tx['gasPrice']
            gas_cost_eth = float(self.web3.from_wei(gas_cost, 'ether'))
            self.total_gas_spent_eth += gas_cost_eth
            
            if receipt['status'] == 1:
                self.successful_trades += 1
                self.buy_count = 0  # Reset buy counter
                logger.info(f"Sell successful! Gas used: {receipt['gasUsed']}")
                return {
                    "success": True,
                    "tx_hash": tx_hash,
                    "gas_used": receipt['gasUsed'],
                    "gas_cost_eth": gas_cost_eth,
                    "block_number": receipt['blockNumber'],
                    "tokens_sold": balance
                }
            else:
                raise TransactionError(f"Transaction failed: {tx_hash}")
                
        except Exception as e:
            logger.exception("Sell failed")
            return {"success": False, "error": str(e)}
    
    async def _ensure_approval(self, token_address: str, spender: str, amount: int):
        """Ensure token approval for spender."""
        token = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
        
        current_allowance = token.functions.allowance(self.wallet.address, spender).call()
        
        if current_allowance < amount:
            logger.info(f"Approving {spender} to spend tokens...")
            
            # Approve max uint256
            max_uint = 2**256 - 1
            
            tx = token.functions.approve(spender, max_uint).build_transaction({
                'from': self.wallet.address,
                'nonce': self.wallet.get_nonce(),
                'gas': 100000,
                'gasPrice': self.web3.eth.gas_price
            })
            
            signed_tx = self.wallet.sign_transaction(tx)
            tx_hash = self.wallet.send_raw_transaction(signed_tx)
            
            receipt = self.wallet.wait_for_transaction(tx_hash)
            
            if receipt['status'] != 1:
                raise TransactionError(f"Approval transaction failed: {tx_hash}")
            
            logger.info(f"Approval successful: {tx_hash}")
            
            # Small delay to ensure state is updated
            await asyncio.sleep(2)
    
    async def _quote_exact_input(
        self,
        token_in: str,
        token_out: str,
        amount_in: int
    ) -> int:
        """
        Get quote for exact input swap.
        In production, use the Uniswap V3 Quoter contract.
        """
        # Simplified - in production you'd call the quoter contract
        # For now, return a placeholder that assumes price discovery
        try:
            # Try to use quoter contract if available
            quoter_abi = [
                {
                    "inputs": [
                        {"internalType": "address", "name": "tokenIn", "type": "address"},
                        {"internalType": "address", "name": "tokenOut", "type": "address"},
                        {"internalType": "uint24", "name": "fee", "type": "uint24"},
                        {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                        {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                    ],
                    "name": "quoteExactInputSingle",
                    "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
            
            quoter = self.web3.eth.contract(
                address=self.web3.to_checksum_address(self.config.quoter_address),
                abi=quoter_abi
            )
            
            amount_out = quoter.functions.quoteExactInputSingle(
                token_in,
                token_out,
                self.config.pool_fee,
                amount_in,
                0
            ).call()
            
            return amount_out
            
        except Exception as e:
            logger.warning(f"Quoter failed, using fallback: {e}")
            # Fallback: return amount_in (assumes 1:1 for safety)
            # In production, you'd want better price discovery
            return int(amount_in * 0.95)  # Conservative 5% discount
    
    def get_stats(self) -> Dict[str, Any]:
        """Get trading statistics."""
        return {
            "buy_count": self.buy_count,
            "total_trades": self.total_trades,
            "successful_trades": self.successful_trades,
            "total_gas_spent_eth": self.total_gas_spent_eth,
            "success_rate": (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        }
