"""
V4 Command Encoding Module
==========================

Handles encoding of commands and inputs for Uniswap V4 Universal Router.

V4 uses a command-based architecture where:
- Commands are single bytes indicating the operation
- Inputs are ABI-encoded bytes for each command
- Multiple commands can be executed atomically

Command Reference:
- 0x30: V4_SWAP - Execute a V4 swap
- 0x0a: PERMIT2_PERMIT - Approve via Permit2 signature
- 0x0c: PERMIT2_TRANSFER_FROM - Transfer via Permit2
- 0x0b: WRAP_ETH - Wrap ETH to WETH
- 0x0d: UNWRAP_WETH - Unwrap WETH to ETH
- 0x04: SWEEP - Sweep tokens to address
- 0x06: PAY_PORTION - Pay protocol fee
"""

from typing import Optional
from eth_abi import encode
from web3 import Web3


class V4Encoder:
    """
    Encodes commands and inputs for Universal Router.
    
    V4 uses a compact encoding scheme to minimize gas costs.
    This class handles all the encoding complexity.
    """
    
    def __init__(self, w3: Web3):
        """
        Initialize encoder.
        
        Args:
            w3: Web3 instance
        """
        self.w3 = w3
    
    def encode_wrap_eth(self, recipient: str, amount: int) -> bytes:
        """
        Encode WRAP_ETH command input.
        
        Args:
            recipient: Address to receive WETH
            amount: Amount of ETH to wrap
            
        Returns:
            Encoded input bytes
        """
        recipient = self.w3.to_checksum_address(recipient)
        return encode(['address', 'uint256'], [recipient, amount])
    
    def encode_unwrap_weth(self, recipient: str, min_amount: int) -> bytes:
        """
        Encode UNWRAP_WETH command input.
        
        Args:
            recipient: Address to receive ETH
            min_amount: Minimum amount to unwrap
            
        Returns:
            Encoded input bytes
        """
        recipient = self.w3.to_checksum_address(recipient)
        return encode(['address', 'uint256'], [recipient, min_amount])
    
    def encode_sweep(self, token: str, recipient: str, min_amount: int) -> bytes:
        """
        Encode SWEEP command input.
        
        Args:
            token: Token to sweep
            recipient: Address to receive tokens
            min_amount: Minimum amount to sweep
            
        Returns:
            Encoded input bytes
        """
        token = self.w3.to_checksum_address(token)
        recipient = self.w3.to_checksum_address(recipient)
        return encode(['address', 'address', 'uint256'], [token, recipient, min_amount])
    
    def encode_permit2_transfer(
        self,
        token: str,
        recipient: str,
        amount: int
    ) -> bytes:
        """
        Encode PERMIT2_TRANSFER_FROM command input.
        
        Args:
            token: Token to transfer
            recipient: Address to receive
            amount: Amount to transfer
            
        Returns:
            Encoded input bytes
        """
        token = self.w3.to_checksum_address(token)
        recipient = self.w3.to_checksum_address(recipient)
        return encode(['address', 'address', 'uint160'], [token, recipient, amount])
    
    def encode_v4_swap(
        self,
        pool_id: Optional[str],
        token_in: str,
        token_out: str,
        fee_tier: int,
        amount_in: int,
        min_amount_out: int,
        recipient: str,
        sqrt_price_limit_x96: int = 0
    ) -> bytes:
        """
        Encode V4_SWAP command input.
        
        This encodes the swap parameters for V4 pools.
        V4 swaps are more complex than V3 due to the lock/unlock pattern.
        
        Args:
            pool_id: Pool ID (bytes32, computed if None)
            token_in: Input token
            token_out: Output token
            fee_tier: Pool fee tier
            amount_in: Input amount
            min_amount_out: Minimum output (slippage protection)
            recipient: Recipient address
            sqrt_price_limit_x96: Price limit (0 for no limit)
            
        Returns:
            Encoded input bytes
        """
        # If pool_id not provided, compute it
        if pool_id is None:
            pool_id = self._compute_pool_id(token_in, token_out, fee_tier)
        
        # Convert pool_id to bytes32
        if pool_id.startswith('0x'):
            pool_id_bytes = bytes.fromhex(pool_id[2:])
        else:
            pool_id_bytes = bytes.fromhex(pool_id)
        pool_id_bytes = pool_id_bytes.rjust(32, b'\x00')
        
        # Determine swap direction
        zero_for_one = self._is_zero_for_one(token_in, token_out)
        
        # Encode swap parameters
        # V4 swap encoding is complex - this is a simplified version
        # Full implementation would encode the full swap callback data
        
        return encode(
            ['bytes32', 'bool', 'int256', 'uint160', 'address'],
            [pool_id_bytes, zero_for_one, amount_in, sqrt_price_limit_x96, recipient]
        )
    
    def encode_v4_swap_exact_in(
        self,
        token_in: str,
        token_out: str,
        fee: int,
        recipient: str,
        deadline: int,
        amount_in: int,
        amount_out_minimum: int,
        sqrt_price_limit_x96: int = 0
    ) -> bytes:
        """
        Encode exact input swap for V4.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            fee: Pool fee tier
            recipient: Recipient address
            deadline: Transaction deadline
            amount_in: Exact input amount
            amount_out_minimum: Minimum output (slippage)
            sqrt_price_limit_x96: Price limit
            
        Returns:
            Encoded swap data
        """
        # This encodes the swap parameters that will be passed to the V4 swap
        return encode(
            ['address', 'address', 'uint24', 'address', 'uint256', 'uint256', 'uint256', 'uint160'],
            [
                self.w3.to_checksum_address(token_in),
                self.w3.to_checksum_address(token_out),
                fee,
                self.w3.to_checksum_address(recipient),
                deadline,
                amount_in,
                amount_out_minimum,
                sqrt_price_limit_x96
            ]
        )
    
    def encode_v4_swap_exact_out(
        self,
        token_in: str,
        token_out: str,
        fee: int,
        recipient: str,
        deadline: int,
        amount_out: int,
        amount_in_maximum: int,
        sqrt_price_limit_x96: int = 0
    ) -> bytes:
        """
        Encode exact output swap for V4.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            fee: Pool fee tier
            recipient: Recipient address
            deadline: Transaction deadline
            amount_out: Exact output amount
            amount_in_maximum: Maximum input (slippage)
            sqrt_price_limit_x96: Price limit
            
        Returns:
            Encoded swap data
        """
        return encode(
            ['address', 'address', 'uint24', 'address', 'uint256', 'uint256', 'uint256', 'uint160'],
            [
                self.w3.to_checksum_address(token_in),
                self.w3.to_checksum_address(token_out),
                fee,
                self.w3.to_checksum_address(recipient),
                deadline,
                amount_out,
                amount_in_maximum,
                sqrt_price_limit_x96
            ]
        )
    
    def encode_permit2_permit(
        self,
        token: str,
        amount: int,
        expiration: int,
        nonce: int,
        spender: str,
        sig_deadline: int,
        signature: bytes
    ) -> bytes:
        """
        Encode PERMIT2_PERMIT command input.
        
        Args:
            token: Token to permit
            amount: Permitted amount
            expiration: Permit expiration timestamp
            nonce: Unique nonce
            spender: Spender address
            sig_deadline: Signature deadline
            signature: EIP-2612 signature
            
        Returns:
            Encoded input bytes
        """
        # Encode the permit details
        permit_details = encode(
            ['address', 'uint160', 'uint48', 'uint48'],
            [self.w3.to_checksum_address(token), amount, expiration, nonce]
        )
        
        # Encode the permit batch
        permit_batch = encode(
            ['tuple(address,uint160,uint48,uint48)[]', 'address', 'uint256'],
            [[permit_details], self.w3.to_checksum_address(spender), sig_deadline]
        )
        
        # Append signature
        return permit_batch + signature
    
    def encode_pay_portion(
        self,
        token: str,
        recipient: str,
        bips: int
    ) -> bytes:
        """
        Encode PAY_PORTION command input.
        
        Used for fee payments.
        
        Args:
            token: Token to pay
            recipient: Fee recipient
            bips: Fee in basis points (100 = 1%)
            
        Returns:
            Encoded input bytes
        """
        return encode(
            ['address', 'address', 'uint256'],
            [
                self.w3.to_checksum_address(token),
                self.w3.to_checksum_address(recipient),
                bips
            ]
        )
    
    def _compute_pool_id(
        self,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int = 60,
        hooks: str = "0x0000000000000000000000000000000000000000"
    ) -> str:
        """
        Compute pool ID from parameters.
        
        Args:
            token0: First token
            token1: Second token
            fee: Fee tier
            tick_spacing: Tick spacing
            hooks: Hooks address
            
        Returns:
            Pool ID as hex string
        """
        # Sort tokens
        token0 = self.w3.to_checksum_address(token0)
        token1 = self.w3.to_checksum_address(token1)
        
        if int(token0, 16) > int(token1, 16):
            token0, token1 = token1, token0
        
        hooks = self.w3.to_checksum_address(hooks)
        
        # Encode and hash
        encoded = encode(
            ['address', 'address', 'uint24', 'int24', 'address'],
            [token0, token1, fee, tick_spacing, hooks]
        )
        
        return self.w3.keccak(encoded).hex()
    
    def _is_zero_for_one(self, token_in: str, token_out: str) -> bool:
        """
        Determine swap direction.
        
        In V4, zero_for_one=True means swapping token0 for token1.
        Token0 is the lexicographically smaller address.
        
        Args:
            token_in: Input token
            token_out: Output token
            
        Returns:
            True if swapping token0 for token1
        """
        token_in = self.w3.to_checksum_address(token_in)
        token_out = self.w3.to_checksum_address(token_out)
        return int(token_in, 16) < int(token_out, 16)


# Command byte values
class Commands:
    """Universal Router command constants."""
    
    # Permit2 commands
    PERMIT2_PERMIT = 0x0a
    PERMIT2_TRANSFER_FROM = 0x0c
    PERMIT2_PERMIT_BATCH = 0x0e
    PERMIT2_TRANSFER_FROM_BATCH = 0x10
    
    # WETH commands
    WRAP_ETH = 0x0b
    UNWRAP_WETH = 0x0d
    
    # Sweep commands
    SWEEP = 0x04
    TRANSFER = 0x05
    PAY_PORTION = 0x06
    
    # V4 commands
    V4_SWAP = 0x30
    
    # V3/V2 commands (for compatibility)
    V3_SWAP_EXACT_IN = 0x00
    V3_SWAP_EXACT_OUT = 0x01
    V2_SWAP_EXACT_IN = 0x08
    V2_SWAP_EXACT_OUT = 0x09
    
    # Utility commands
    SEAPOLE = 0x13
    OWNER_CHECK_721 = 0x15
    OWNER_CHECK_1155 = 0x16
    SWEEP_ERC721 = 0x19
    SWEEP_ERC1155 = 0x1a
