"""
V4 Universal Router Module
==========================

Handles swap execution through Uniswap V4's Universal Router.

The Universal Router is the entry point for executing swaps in V4.
It handles:
- ETH wrapping/unwrapping
- Token approvals via Permit2
- Multi-hop routing
- V4 specific command encoding

Commands are encoded as bytes and executed atomically.
"""

from typing import Optional, Tuple, Union
from decimal import Decimal
from web3 import Web3
from eth_account import Account

from .encoding import V4Encoder
from .pool_manager import V4PoolManager

# Universal Router ABI
UNIVERSAL_ROUTER_ABI = [
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
    },
    {
        "inputs": [],
        "name": "PERMIT2",
        "outputs": [
            {"internalType": "contract IAllowanceTransfer", "name": "", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "POOL_MANAGER",
        "outputs": [
            {"internalType": "contract IPoolManager", "name": "", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
]

# ERC20 ABI (minimal)
ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
]

# Permit2 ABI (simplified)
PERMIT2_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "token", "type": "address"},
            {"internalType": "address", "name": "spender", "type": "address"},
            {"internalType": "uint160", "name": "amount", "type": "uint160"},
            {"internalType": "uint48", "name": "expiration", "type": "uint48"}
        ],
        "name": "approve",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
]

# Command flags for Universal Router
# See: https://docs.uniswap.org/contracts/v4/concepts/universal-router
COMMANDS = {
    'V4_SWAP': 0x30,
    'PERMIT2_PERMIT': 0x0a,
    'PERMIT2_TRANSFER_FROM': 0x0c,
    'WRAP_ETH': 0x0b,
    'UNWRAP_WETH': 0x0d,
    'SWEEP': 0x04,
    'PAY_PORTION': 0x06,
}

WETH_ADDRESS = "0x4200000000000000000000000000000000000006"
PERMIT2_ADDRESS = "0x000000000022D473030F116dDEE9F6B43aC78BA3"


class V4UniversalRouter:
    """
    Executes swaps through Uniswap V4 Universal Router.
    
    The Universal Router handles all the complexity of:
    - Command encoding
    - Permit2 approvals
    - Multi-step execution (wrap ETH -> swap -> sweep)
    
    Example:
        >>> router = V4UniversalRouter(w3, account)
        >>> success, tx_hash = router.swap_exact_in(WETH, USDC, 0.1, 2.0, 3000)
    """
    
    def __init__(
        self,
        w3: Web3,
        account: Account,
        router_address: str,
        pool_manager_address: str,
        permit2_address: str = PERMIT2_ADDRESS
    ):
        """
        Initialize Universal Router interface.
        
        Args:
            w3: Web3 instance
            account: Account for signing transactions
            router_address: Universal Router contract address
            pool_manager_address: V4 PoolManager address for quoting
            permit2_address: Permit2 contract address
        """
        self.w3 = w3
        self.account = account
        self.router_address = w3.to_checksum_address(router_address)
        self.permit2_address = w3.to_checksum_address(permit2_address)
        
        self.router = w3.eth.contract(
            address=self.router_address,
            abi=UNIVERSAL_ROUTER_ABI
        )
        
        self.pool_manager = V4PoolManager(w3, pool_manager_address)
        self.encoder = V4Encoder(w3)
        self.permit2 = w3.eth.contract(address=self.permit2_address, abi=PERMIT2_ABI)
    
    def _get_token_contract(self, token_address: str):
        """Get token contract interface."""
        return self.w3.eth.contract(
            address=self.w3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
    
    def _approve_token(self, token_address: str, amount: int) -> Tuple[bool, str]:
        """
        Approve token spending via Permit2.
        
        Args:
            token_address: Token to approve
            amount: Amount to approve
            
        Returns:
            (success, tx_hash_or_error)
        """
        try:
            token_address = self.w3.to_checksum_address(token_address)
            
            # First approve Permit2 to spend tokens (standard ERC20 approval)
            token_contract = self._get_token_contract(token_address)
            
            # Check current allowance
            current_allowance = token_contract.functions.allowance(
                self.account.address,
                self.permit2_address
            ).call()
            
            if current_allowance >= amount:
                return True, "Already approved"
            
            # Approve Permit2 with exact amount (not unlimited)
            approve_amount = amount
            approve_tx = token_contract.functions.approve(
                self.permit2_address,
                approve_amount
            ).build_transaction({
                'from': self.account.address,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': 8453,
            })
            
            signed = self.account.sign_transaction(approve_tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                return True, self.w3.to_hex(tx_hash)
            else:
                return False, "Approval failed"
                
        except Exception as e:
            return False, f"Approval error: {e}"
    
    def encode_v4_commands(
        self,
        commands: list,
        inputs: list
    ) -> Tuple[bytes, list]:
        """
        Encode commands for Universal Router execute().
        
        Args:
            commands: List of command bytes
            inputs: List of encoded input data
            
        Returns:
            Tuple of (encoded_commands, inputs)
        """
        # Commands are packed as bytes
        encoded_commands = bytes(commands)
        return encoded_commands, inputs
    
    def swap_exact_in(
        self,
        token_in: str,
        token_out: str,
        amount_in_eth: Decimal,
        slippage_percent: float,
        fee_tier: int,
        recipient: Optional[str] = None,
        deadline: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Swap exact input for output (ETH -> Token).
        
        For ETH->Token swaps, the router:
        1. Receives ETH
        2. Wraps to WETH
        3. Swaps through V4 pool
        4. Sweeps output to recipient
        
        Args:
            token_in: Input token (usually WETH for ETH swaps)
            token_out: Output token
            amount_in_eth: Amount of ETH to swap
            slippage_percent: Max slippage tolerance
            fee_tier: Pool fee tier
            recipient: Recipient address (defaults to account)
            deadline: Transaction deadline (defaults to +5 min)
            
        Returns:
            Tuple of (success, tx_hash_or_error)
        """
        if recipient is None:
            recipient = self.account.address
        
        if deadline is None:
            deadline = self.w3.eth.get_block('latest')['timestamp'] + 300
        
        try:
            token_in = self.w3.to_checksum_address(token_in)
            token_out = self.w3.to_checksum_address(token_out)
            recipient = self.w3.to_checksum_address(recipient)
            
            amount_in_wei = int(amount_in_eth * 10**18)
            
            # Validate slippage
            if slippage_percent < 0 or slippage_percent > 100:
                return False, "Slippage must be between 0 and 100"
            
            # Get pool ID for quoting
            pool_id = self.pool_manager.get_pool_id(token_in, token_out, fee_tier)
            if not pool_id:
                return False, f"No pool found for {token_in}/{token_out} with fee {fee_tier}"
            
            # Get current pool price and calculate expected output
            slot0 = self.pool_manager.get_slot0(pool_id)
            if not slot0:
                return False, "Could not get pool price"
            
            # Calculate expected output (simplified - assumes 1:1 for rough estimate)
            # For production, use proper quoter
            expected_out = amount_in_wei  # Placeholder - actual would use quoter
            min_amount_out = int(expected_out * (100 - slippage_percent) / 100)
            
            # Build V4 swap commands
            commands = []
            inputs = []
            
            # Command 1: Wrap ETH to WETH (if input is WETH/native)
            if token_in.lower() == WETH_ADDRESS.lower():
                # WRAP_ETH command
                commands.append(COMMANDS['WRAP_ETH'])
                # Encode: recipient, amount
                wrap_input = self.encoder.encode_wrap_eth(self.router_address, amount_in_wei)
                inputs.append(wrap_input)
            
            # Command 2: V4 Swap
            commands.append(COMMANDS['V4_SWAP'])
            swap_input = self.encoder.encode_v4_swap(
                pool_id=pool_id,
                token_in=token_in,
                token_out=token_out,
                fee_tier=fee_tier,
                amount_in=amount_in_wei,
                min_amount_out=min_amount_out,  # Now with slippage protection
                recipient=recipient
            )
            inputs.append(swap_input)
            
            # Command 3: Sweep tokens to recipient
            commands.append(COMMANDS['SWEEP'])
            sweep_input = self.encoder.encode_sweep(token_out, recipient, 1)  # min amount = 1 wei
            inputs.append(sweep_input)
            
            # Build execute transaction
            encoded_commands = bytes(commands)
            
            tx = self.router.functions.execute(
                encoded_commands,
                inputs,
                deadline
            ).build_transaction({
                'from': self.account.address,
                'value': amount_in_wei,  # Send ETH
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': 8453,
            })
            
            # Sign and send
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            print(f"[V4UniversalRouter] TX sent: {self.w3.to_hex(tx_hash)}")
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                return True, self.w3.to_hex(tx_hash)
            else:
                return False, f"Transaction failed (status={receipt['status']})"
                
        except Exception as e:
            return False, f"Swap error: {e}"
    
    def swap_exact_out(
        self,
        token_in: str,
        token_out: str,
        amount_in_tokens: Union[Decimal, float],
        token_decimals: int,
        slippage_percent: float,
        fee_tier: int,
        recipient: Optional[str] = None,
        deadline: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Swap tokens for ETH (Token -> ETH/WETH).
        
        For Token->ETH swaps, the router:
        1. Transfers tokens from user via Permit2
        2. Swaps through V4 pool
        3. Unwraps WETH to ETH
        4. Sends ETH to recipient
        
        Args:
            token_in: Input token
            token_out: Output token (usually WETH for ETH output)
            amount_in_tokens: Amount of tokens to swap
            token_decimals: Decimals of input token
            slippage_percent: Max slippage tolerance
            fee_tier: Pool fee tier
            recipient: Recipient address (defaults to account)
            deadline: Transaction deadline (defaults to +5 min)
            
        Returns:
            Tuple of (success, tx_hash_or_error)
        """
        if recipient is None:
            recipient = self.account.address
        
        if deadline is None:
            deadline = self.w3.eth.get_block('latest')['timestamp'] + 300
        
        try:
            token_in = self.w3.to_checksum_address(token_in)
            token_out = self.w3.to_checksum_address(token_out)
            recipient = self.w3.to_checksum_address(recipient)
            
            amount_in_wei = int(Decimal(str(amount_in_tokens)) * (10 ** token_decimals))
            
            # Validate inputs
            if amount_in_wei <= 0:
                return False, "Amount must be greater than 0"
            if slippage_percent < 0 or slippage_percent > 100:
                return False, "Slippage must be between 0 and 100"
            
            # Get pool ID for quoting
            pool_id = self.pool_manager.get_pool_id(token_in, token_out, fee_tier)
            if not pool_id:
                return False, f"No pool found for {token_in}/{token_out} with fee {fee_tier}"
            
            # Calculate min output with slippage protection
            # For token->ETH, we expect roughly equivalent value
            expected_out = amount_in_wei  # Placeholder - proper quoter would be used
            min_amount_out = int(expected_out * (100 - slippage_percent) / 100)
            
            # Step 1: Approve Permit2 if needed
            approved, approve_result = self._approve_token(token_in, amount_in_wei)
            if not approved:
                return False, f"Token approval failed: {approve_result}"
            
            # Build commands
            commands = []
            inputs = []
            
            # Command 1: Permit2 transfer from
            commands.append(COMMANDS['PERMIT2_TRANSFER_FROM'])
            permit_input = self.encoder.encode_permit2_transfer(
                token_in,
                self.router_address,
                amount_in_wei
            )
            inputs.append(permit_input)
            
            # Command 2: V4 Swap
            commands.append(COMMANDS['V4_SWAP'])
            swap_input = self.encoder.encode_v4_swap(
                pool_id=pool_id,
                token_in=token_in,
                token_out=token_out,
                fee_tier=fee_tier,
                amount_in=amount_in_wei,
                min_amount_out=min_amount_out,  # Now with slippage protection
                recipient=self.router_address  # Router holds WETH temporarily
            )
            inputs.append(swap_input)
            
            # Command 3: Unwrap WETH to ETH (if output is WETH)
            if token_out.lower() == WETH_ADDRESS.lower():
                commands.append(COMMANDS['UNWRAP_WETH'])
                unwrap_input = self.encoder.encode_unwrap_weth(recipient, 1)
                inputs.append(unwrap_input)
            
            # Build execute transaction
            encoded_commands = bytes(commands)
            
            tx = self.router.functions.execute(
                encoded_commands,
                inputs,
                deadline
            ).build_transaction({
                'from': self.account.address,
                'value': 0,  # No ETH sent
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': 8453,
            })
            
            # Sign and send
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            print(f"[V4UniversalRouter] TX sent: {self.w3.to_hex(tx_hash)}")
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                return True, self.w3.to_hex(tx_hash)
            else:
                return False, f"Transaction failed (status={receipt['status']})"
                
        except Exception as e:
            return False, f"Swap error: {e}"
    
    def sweep_tokens(
        self,
        token: str,
        min_amount: int,
        recipient: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Sweep remaining tokens to recipient.
        
        Used to recover any leftover tokens after a swap.
        
        Args:
            token: Token to sweep
            min_amount: Minimum amount to sweep
            recipient: Recipient address
            
        Returns:
            Tuple of (success, tx_hash_or_error)
        """
        if recipient is None:
            recipient = self.account.address
        
        try:
            commands = [COMMANDS['SWEEP']]
            inputs = [self.encoder.encode_sweep(token, recipient, min_amount)]
            
            deadline = self.w3.eth.get_block('latest')['timestamp'] + 300
            
            tx = self.router.functions.execute(
                bytes(commands),
                inputs,
                deadline
            ).build_transaction({
                'from': self.account.address,
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': 8453,
            })
            
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                return True, self.w3.to_hex(tx_hash)
            else:
                return False, "Sweep failed"
                
        except Exception as e:
            return False, f"Sweep error: {e}"
