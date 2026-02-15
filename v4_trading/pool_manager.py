"""
V4 Pool Manager Module
======================

Handles all interactions with the Uniswap V4 PoolManager contract.

The PoolManager is the core contract in V4 that manages all pools.
Unlike V3 where each pool is a separate contract, V4 uses a single
contract with pool IDs to identify pools.

Pool ID is computed as: keccak256(token0, token1, fee, tickSpacing, hooks)
"""

from typing import Optional, Tuple, Dict
from eth_abi import encode
from web3 import Web3

# PoolManager ABI (core functions)
POOL_MANAGER_ABI = [
    {
        "inputs": [
            {"internalType": "PoolId", "name": "id", "type": "bytes32"}
        ],
        "name": "getSlot0",
        "outputs": [
            {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
            {"internalType": "int24", "name": "tick", "type": "int24"},
            {"internalType": "uint24", "name": "protocolFee", "type": "uint24"},
            {"internalType": "uint24", "name": "swapFee", "type": "uint24"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "PoolId", "name": "id", "type": "bytes32"}
        ],
        "name": "getLiquidity",
        "outputs": [
            {"internalType": "uint128", "name": "liquidity", "type": "uint128"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "lockCaller", "type": "address"}
        ],
        "name": "lock",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes", "name": "rawCallbackData", "type": "bytes"}
        ],
        "name": "unlock",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "recipient", "type": "address"},
            {"internalType": "BalanceDelta", "name": "delta", "type": "int256"},
            {"internalType": "bytes", "name": "hookData", "type": "bytes"}
        ],
        "name": "take",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "token", "type": "address"},
            {"internalType": "address", "name": "recipient", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "mint",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "token", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "burn",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "PoolId", "name": "id", "type": "bytes32"},
            {"internalType": "bool", "name": "zeroForOne", "type": "bool"},
            {"internalType": "int256", "name": "amountSpecified", "type": "int256"},
            {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"},
            {"internalType": "bytes", "name": "hookData", "type": "bytes"}
        ],
        "name": "swap",
        "outputs": [
            {"internalType": "BalanceDelta", "name": "delta", "type": "int256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "PoolId", "name": "id", "type": "bytes32"},
            {"indexed": True, "internalType": "address", "name": "token0", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "token1", "type": "address"},
            {"indexed": False, "internalType": "uint24", "name": "fee", "type": "uint24"},
            {"indexed": False, "internalType": "int24", "name": "tickSpacing", "type": "int24"},
            {"indexed": False, "internalType": "address", "name": "hooks", "type": "address"}
        ],
        "name": "Initialize",
        "type": "event"
    },
]

# Default tick spacing for fee tiers
FEE_TO_TICK_SPACING = {
    100: 1,      # 0.01%
    500: 10,     # 0.05%
    3000: 60,    # 0.3%
    10000: 200   # 1%
}


class V4PoolManager:
    """
    Manages interactions with Uniswap V4 PoolManager.
    
    Key responsibilities:
    - Compute pool IDs from token pair + fee
    - Read pool state (slot0, liquidity)
    - Execute swaps through PoolManager (advanced)
    
    Example:
        >>> manager = V4PoolManager(w3)
        >>> pool_id = manager.get_pool_id(WETH, USDC, 3000)
        >>> slot0 = manager.get_slot0(pool_id)
        >>> print(f"Price: {slot0['sqrtPriceX96']}")
    """
    
    def __init__(self, w3: Web3, pool_manager_address: str):
        """
        Initialize PoolManager interface.
        
        Args:
            w3: Web3 instance
            pool_manager_address: PoolManager contract address
        """
        self.w3 = w3
        self.pool_manager_address = w3.to_checksum_address(pool_manager_address)
        self.pool_manager = w3.eth.contract(
            address=self.pool_manager_address,
            abi=POOL_MANAGER_ABI
        )
    
    def get_pool_id(
        self,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: Optional[int] = None,
        hooks: str = "0x0000000000000000000000000000000000000000"
    ) -> str:
        """
        Compute the pool ID (PoolId) for a V4 pool.
        
        In V4, pools are identified by a bytes32 hash of pool parameters
        rather than by address like in V3.
        
        Args:
            token0: First token address (will be sorted)
            token1: Second token address (will be sorted)
            fee: Fee tier (100, 500, 3000, 10000)
            tick_spacing: Tick spacing (auto-computed from fee if not provided)
            hooks: Hooks contract address (zero address if none)
            
        Returns:
            Pool ID as hex string (bytes32)
        """
        # Sort tokens (token0 < token1)
        token0 = self.w3.to_checksum_address(token0)
        token1 = self.w3.to_checksum_address(token1)
        
        if int(token0, 16) > int(token1, 16):
            token0, token1 = token1, token0
        
        # Get tick spacing from fee tier if not provided
        if tick_spacing is None:
            tick_spacing = FEE_TO_TICK_SPACING.get(fee, 60)
        
        hooks = self.w3.to_checksum_address(hooks)
        
        # Compute pool ID: keccak256(encode(token0, token1, fee, tickSpacing, hooks))
        # Encode as packed bytes
        encoded = encode(
            ['address', 'address', 'uint24', 'int24', 'address'],
            [token0, token1, fee, tick_spacing, hooks]
        )
        
        pool_id = self.w3.keccak(encoded).hex()
        return pool_id
    
    def get_slot0(self, pool_id: str) -> Optional[Dict]:
        """
        Get current pool state (slot0).
        
        Returns sqrtPriceX96, tick, and fee info.
        
        Args:
            pool_id: Pool ID (bytes32 hex string)
            
        Returns:
            Dictionary with pool state or None if pool doesn't exist
        """
        try:
            # Convert hex string to bytes32
            if pool_id.startswith('0x'):
                pool_id_bytes = bytes.fromhex(pool_id[2:])
            else:
                pool_id_bytes = bytes.fromhex(pool_id)
            
            # Pad to 32 bytes
            pool_id_bytes = pool_id_bytes.rjust(32, b'\x00')
            
            # Call getSlot0
            result = self.pool_manager.functions.getSlot0(pool_id_bytes).call()
            
            return {
                'sqrtPriceX96': result[0],
                'tick': result[1],
                'protocolFee': result[2],
                'swapFee': result[3],
            }
        except Exception as e:
            # Pool likely doesn't exist
            return None
    
    def get_liquidity(self, pool_id: str) -> Optional[int]:
        """
        Get total liquidity in the pool.
        
        Args:
            pool_id: Pool ID (bytes32 hex string)
            
        Returns:
            Liquidity amount or None if pool doesn't exist
        """
        try:
            # Convert hex string to bytes32
            if pool_id.startswith('0x'):
                pool_id_bytes = bytes.fromhex(pool_id[2:])
            else:
                pool_id_bytes = bytes.fromhex(pool_id)
            
            # Pad to 32 bytes
            pool_id_bytes = pool_id_bytes.rjust(32, b'\x00')
            
            return self.pool_manager.functions.getLiquidity(pool_id_bytes).call()
        except Exception as e:
            return None
    
    def pool_exists(self, token0: str, token1: str, fee: int) -> bool:
        """
        Check if a pool exists.
        
        Args:
            token0: First token
            token1: Second token
            fee: Fee tier
            
        Returns:
            True if pool exists, False otherwise
        """
        pool_id = self.get_pool_id(token0, token1, fee)
        slot0 = self.get_slot0(pool_id)
        return slot0 is not None
    
    def get_pool_tick_spacing(self, fee: int) -> int:
        """
        Get the tick spacing for a fee tier.
        
        Args:
            fee: Fee tier
            
        Returns:
            Tick spacing
        """
        return FEE_TO_TICK_SPACING.get(fee, 60)
    
    def swap(
        self,
        pool_id: str,
        zero_for_one: bool,
        amount_specified: int,
        sqrt_price_limit_x96: int = 0,
        hook_data: bytes = b'',
        from_account=None
    ) -> Tuple[bool, str]:
        """
        Execute a swap directly through PoolManager.
        
        NOTE: This is for advanced use. Most users should use UniversalRouter
        via V4UniversalRouter.swap_exact_in/swap_exact_out instead.
        
        Requires the PoolManager to be unlocked first, which means you need
        to implement a lock callback pattern.
        
        Args:
            pool_id: Pool ID
            zero_for_one: True if swapping token0 for token1
            amount_specified: Amount to swap (positive = exact input, negative = exact output)
            sqrt_price_limit_x96: Price limit (0 for no limit)
            hook_data: Data to pass to hooks
            from_account: Account to use (defaults to None)
            
        Returns:
            Tuple of (success, delta_or_error)
        """
        try:
            # Convert pool_id to bytes
            if pool_id.startswith('0x'):
                pool_id_bytes = bytes.fromhex(pool_id[2:])
            else:
                pool_id_bytes = bytes.fromhex(pool_id)
            pool_id_bytes = pool_id_bytes.rjust(32, b'\x00')
            
            # Build swap parameters
            # Note: In V4, swaps happen inside a lock context
            # This requires implementing the lock/unlock pattern
            # For direct swaps, use UniversalRouter instead
            
            if from_account is None:
                return False, "from_account required for PoolManager swaps"
            
            # Build the swap call
            tx = self.pool_manager.functions.swap(
                pool_id_bytes,
                zero_for_one,
                amount_specified,
                sqrt_price_limit_x96,
                hook_data
            ).build_transaction({
                'from': from_account.address,
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(from_account.address),
                'chainId': 8453,
            })
            
            # Sign and send
            signed = from_account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                return True, self.w3.to_hex(tx_hash)
            else:
                return False, f"Transaction failed (status={receipt['status']})"
                
        except Exception as e:
            return False, f"Swap error: {e}"


# COMPUTE Pool constant for reference
COMPUTE_POOL_ID = "0x40332cd73d9c79b34aa477cbd7e6962387dcfda042a12c72ad94bc58262023bf"
