"""
Swarm Wallet Module
==================
Distributed trading wallet management for volume generation.

Features:
- Create multiple trading wallets
- Distribute funds from main wallet
- Cycle through wallets for trades
- Reclaim all funds safely
- Never dissolve non-zero balance wallets

Security:
- All keys encrypted with PBKDF2 + Fernet
- Main wallet never exposed in code
- Balance verification before all operations
- Comprehensive audit logging
"""

from .manager import SwarmManager, SwarmWallet, SwarmSecurity

__all__ = ["SwarmManager", "SwarmWallet", "SwarmSecurity"]
