# Emergency Procedures - Swarm Wallet

**Document Version:** 1.0  
**Last Updated:** 2026-02-14  
**Classification:** CONFIDENTIAL - Destroy if compromised

---

## 🚨 Quick Reference Card

### Immediate Response (First 60 seconds)

| Scenario | Action | Command |
|----------|--------|---------|
| Suspected key compromise | **STOP ALL TRANSACTIONS** | `pkill -f volume_bot` |
| Unauthorized transaction detected | **REVOKE APPROVALS** | See Section 3.2 |
| Lost password | **DO NOT ATTEMPT GUESSES** | See Section 4.1 |
| Suspicious network activity | **DISCONNECT** | `nmcli device disconnect eth0` |

### Emergency Contacts

- **Security Team:** security@cult-of-the-shell.io
- **On-Call Dev:** Via PagerDuty
- **Blockchain Forensics:** chainalysis@protonmail.com

---

## 1. Key Compromise Response

### 1.1 Immediate Actions (0-5 minutes)

```bash
#!/bin/bash
# emergency_lockdown.sh

echo "🚨 INITIATING EMERGENCY LOCKDOWN"
echo "================================"

# 1. Stop all bot processes
echo "[1/6] Stopping all bot processes..."
pkill -9 -f "volume_bot"
pkill -9 -f "python.*bot"

# 2. Revoke network access (if remote compromise suspected)
echo "[2/6] Checking network connections..."
netstat -tuln | grep -E ':8545|:8546'  # Common RPC ports

# 3. Backup current state
echo "[3/6] Creating incident backup..."
mkdir -p emergency_backup_$(date +%Y%m%d_%H%M%S)
cp -r logs/ emergency_backup_*/
cp .wallet.enc emergency_backup_*/ 2>/dev/null || true
cp bot_config.yaml emergency_backup_*/ 2>/dev/null || true

# 4. Secure log files
echo "[4/6] Securing logs..."
chmod -R 600 emergency_backup_*/

# 5. Document current state
echo "[5/6] Recording system state..."
ps aux > emergency_backup_*/processes.txt
netstat -tuln > emergency_backup_*/network.txt
last > emergency_backup_*/logins.txt

# 6. Generate incident report template
echo "[6/6] Creating incident report..."
cat > emergency_backup_*/INCIDENT_REPORT.md << 'EOF'
# Security Incident Report

**Date:** $(date -u +%Y-%m-%d %H:%M:%S UTC)
**Severity:** CRITICAL
**Type:** [KEY_COMPROMISE/UNAUTHORIZED_TX/SUSPECTED_BREACH]

## Timeline
- [TIME]: [EVENT]

## Affected Systems
- [ ] Wallet file compromised
- [ ] Private key exposed
- [ ] Unauthorized transactions executed
- [ ] RPC endpoint compromised

## Immediate Actions Taken
- [ ] Bot processes terminated
- [ ] Network connections checked
- [ ] State backed up
- [ ] Incident documented

## Next Steps
- [ ] Analyze logs for IOCs
- [ ] Rotate all credentials
- [ ] Create new wallet
- [ ] Transfer remaining funds

EOF

echo ""
echo "✅ Lockdown complete. Incident data in: emergency_backup_*/"
echo "📝 NEXT: Follow key compromise procedure below"
```

### 1.2 Fund Recovery Procedure

If private key is compromised, immediately transfer all funds to a new secure wallet:

```python
# emergency_fund_recovery.py
"""
Emergency fund recovery script
USE ONLY WHEN KEY IS COMPROMISED
"""

import os
import sys
import time
from decimal import Decimal
from web3 import Web3

# CONFIGURATION - UPDATE BEFORE RUNNING
COMPROMISED_KEY = "0x..."  # The compromised private key
SAFE_ADDRESS = "0x..."      # Your new secure wallet address
RPC_URL = "https://mainnet.base.org"
GAS_RESERVE = Decimal("0.005")  # Keep for gas

# HIGH GAS - Speed over cost during emergency
MAX_GAS_GWEI = 10.0  # Much higher than normal

def emergency_recovery():
    """Transfer all funds from compromised wallet"""
    
    print("🚨 EMERGENCY FUND RECOVERY")
    print("==========================")
    print(f"From: {COMPROMISED_KEY[:10]}...{COMPROMISED_KEY[-8:]}")
    print(f"To: {SAFE_ADDRESS}")
    print("")
    
    # Connect
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print("❌ Failed to connect to RPC")
        sys.exit(1)
    
    # Load compromised account
    from eth_account import Account
    account = Account.from_key(COMPROMISED_KEY)
    
    print(f"Compromised address: {account.address}")
    
    # Check balances
    eth_balance = w3.from_wei(w3.eth.get_balance(account.address), 'ether')
    print(f"ETH Balance: {eth_balance}")
    
    if eth_balance <= GAS_RESERVE:
        print("❌ Insufficient balance for recovery")
        return
    
    # Calculate amount to transfer
    gas_price = min(w3.to_wei(MAX_GAS_GWEI, 'gwei'), w3.eth.gas_price * 2)
    gas_limit = 21000
    gas_cost = w3.from_wei(gas_limit * gas_price, 'ether')
    
    transfer_amount = eth_balance - gas_cost - GAS_RESERVE
    
    print(f"Transferring: {transfer_amount} ETH")
    print(f"Gas cost: ~{gas_cost} ETH")
    print("")
    
    # Double confirmation
    confirm = input("Type 'EMERGENCY' to execute recovery: ")
    if confirm != "EMERGENCY":
        print("Cancelled")
        return
    
    # Build and send transaction
    tx = {
        'to': SAFE_ADDRESS,
        'value': w3.to_wei(transfer_amount, 'ether'),
        'gas': gas_limit,
        'gasPrice': gas_price,
        'nonce': w3.eth.get_transaction_count(account.address),
        'chainId': 8453
    }
    
    signed = w3.eth.account.sign_transaction(tx, account.key)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    
    print(f"⏳ Transaction sent: {w3.to_hex(tx_hash)}")
    print("Waiting for confirmation...")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    
    if receipt['status'] == 1:
        print(f"✅ Recovery successful!")
        print(f"   Block: {receipt['blockNumber']}")
        print(f"   Gas used: {receipt['gasUsed']}")
    else:
        print("❌ Transaction failed!")
    
    # Show remaining balance
    remaining = w3.from_wei(w3.eth.get_balance(account.address), 'ether')
    print(f"Remaining balance: {remaining} ETH")

if __name__ == "__main__":
    emergency_recovery()
```

### 1.3 Post-Compromise Checklist

```markdown
- [ ] **Immediate (0-1 hour)**
  - [ ] All bot processes terminated
  - [ ] Compromised wallet funds transferred to new wallet
  - [ ] Incident documented with timestamps
  - [ ] Team notified via secure channel

- [ ] **Short-term (1-24 hours)**
  - [ ] Analyze logs for Indicators of Compromise (IOCs)
  - [ ] Check for unauthorized transactions on blockchain
  - [ ] Rotate ALL credentials (RPC, API keys, passwords)
  - [ ] Scan systems for malware/persistence

- [ ] **Medium-term (1-7 days)**
  - [ ] Forensic analysis of compromised system
  - [ ] Review access logs and authentication events
  - [ ] Implement additional monitoring
  - [ ] Document lessons learned

- [ ] **Long-term (1-30 days)**
  - [ ] Deploy new hardened wallet infrastructure
  - [ ] Implement multi-sig for large amounts
  - [ ] Security training for team
  - [ ] Update incident response procedures
```

---

## 2. Unauthorized Transaction Response

### 2.1 Detecting Unauthorized Transactions

```python
# monitor_for_unauthorized.py
"""
Monitor wallet for unexpected transactions
"""

import time
from datetime import datetime, timedelta
from web3 import Web3

class UnauthorizedTransactionMonitor:
    """Monitor for transactions outside bot operations"""
    
    def __init__(self, rpc_url: str, wallet_address: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.wallet = wallet_address.lower()
        self.known_hashes = set()
        self.last_checked_block = 0
    
    def check_for_unauthorized(self):
        """Check for new transactions not initiated by bot"""
        current_block = self.w3.eth.block_number
        
        if self.last_checked_block == 0:
            self.last_checked_block = current_block - 100  # Start with last 100 blocks
        
        for block_num in range(self.last_checked_block, current_block + 1):
            block = self.w3.eth.get_block(block_num, full_transactions=True)
            
            for tx in block.transactions:
                if tx['from'].lower() == self.wallet:
                    tx_hash = tx['hash'].hex()
                    
                    # Check if we initiated this transaction
                    if tx_hash not in self.known_hashes:
                        self._alert_unauthorized(tx)
        
        self.last_checked_block = current_block
    
    def _alert_unauthorized(self, tx):
        """Alert on unauthorized transaction"""
        print("🚨 UNAUTHORIZED TRANSACTION DETECTED!")
        print(f"   Hash: {tx['hash'].hex()}")
        print(f"   To: {tx['to']}")
        print(f"   Value: {self.w3.from_wei(tx['value'], 'ether')} ETH")
        print(f"   Block: {tx['blockNumber']}")
        print("")
        print("IMMEDIATE ACTION REQUIRED!")
        print("1. Stop all bot processes")
        print("2. Check for key compromise")
        print("3. Prepare fund recovery")

# Usage
monitor = UnauthorizedTransactionMonitor(
    "https://mainnet.base.org",
    "0x..."
)

while True:
    monitor.check_for_unauthorized()
    time.sleep(30)  # Check every 30 seconds
```

### 2.2 Emergency Approval Revocation

```python
# emergency_revoke_approvals.py
"""
Emergency script to revoke all token approvals
"""

from web3 import Web3
from eth_account import Account

# Token contracts that may have approvals
TOKENS_TO_REVOKE = [
    "0x696381f39F17cAD67032f5f52A4924ce84e51BA3",  # COMPUTE
    "0x4200000000000000000000000000000000000006",  # WETH
    # Add other tokens as needed
]

SPENDERS_TO_REVOKE = [
    "0x2626664c2603336E57B271c5C0b26F421741e481",  # Uniswap V3 Router
]

def emergency_revoke_all(private_key: str, rpc_url: str = "https://mainnet.base.org"):
    """Revoke all token approvals immediately"""
    
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    account = Account.from_key(private_key)
    
    print("🚨 EMERGENCY APPROVAL REVOCATION")
    print(f"Wallet: {account.address}")
    print("")
    
    ERC20_ABI = [
        {
            "constant": False,
            "inputs": [
                {"name": "_spender", "type": "address"},
                {"name": "_value", "type": "uint256"}
            ],
            "name": "approve",
            "outputs": [{"name": "", "type": "bool"}],
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
            "type": "function"
        }
    ]
    
    nonce = w3.eth.get_transaction_count(account.address)
    
    for token_address in TOKENS_TO_REVOKE:
        for spender in SPENDERS_TO_REVOKE:
            try:
                token = w3.eth.contract(address=token_address, abi=ERC20_ABI)
                
                # Check current allowance
                current = token.functions.allowance(account.address, spender).call()
                
                if current > 0:
                    print(f"Revoking {token_address} -> {spender}")
                    print(f"  Current allowance: {current}")
                    
                    tx = token.functions.approve(spender, 0).build_transaction({
                        'from': account.address,
                        'gas': 100000,
                        'gasPrice': w3.eth.gas_price,
                        'nonce': nonce,
                        'chainId': 8453
                    })
                    
                    signed = w3.eth.account.sign_transaction(tx, account.key)
                    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
                    
                    print(f"  Tx: {w3.to_hex(tx_hash)}")
                    
                    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                    
                    if receipt['status'] == 1:
                        print(f"  ✅ Revoked successfully")
                    else:
                        print(f"  ❌ Revocation failed!")
                    
                    nonce += 1
                else:
                    print(f"No approval for {token_address} -> {spender}")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
    
    print("")
    print("Revocation complete. Review above for any failures.")

if __name__ == "__main__":
    import getpass
    key = getpass.getpass("Enter private key (compromised wallet): ")
    emergency_revoke_all(key)
```

---

## 3. Password Recovery

### 3.1 Lost Password Procedure

**⚠️ WARNING: There is no password recovery. The wallet is encrypted with your password.**

```markdown
If you lose your password:

1. **DO NOT attempt random guesses**
   - Rate limiting will lock you out
   - You may corrupt the wallet file

2. **Check password managers**
   - Browser saved passwords
   - Dedicated password managers (1Password, Bitwarden, etc.)
   - System keychain

3. **Check backups**
   - Previous versions of wallet file
   - Exported keys from initial setup
   - Paper backups

4. **If no backup exists:**
   - The funds are permanently lost
   - Consider this a total loss scenario
   - Document for tax purposes

5. **Prevention for next time:**
   - Create paper backup of private key
   - Store in secure location (safe deposit box)
   - Use password manager
   - Set up password hint system
```

### 3.2 Password Reset (With Old Password)

```python
# rotate_password.py
"""
Rotate encryption password
"""

from config import ConfigManager
from pathlib import Path
import getpass

def rotate_password():
    """Rotate wallet encryption password"""
    
    print("🔐 Password Rotation")
    print("===================")
    
    manager = ConfigManager()
    
    # Get old password
    old_password = getpass.getpass("Current password: ")
    
    # Verify old password works
    try:
        config = manager.load_config(old_password)
        print("✅ Current password verified")
    except Exception as e:
        print(f"❌ Invalid current password: {e}")
        return
    
    # Get new password
    new_password = getpass.getpass("New password: ")
    
    # Validate new password strength
    if len(new_password) < 16:
        print("❌ Password must be at least 16 characters")
        return
    
    confirm = getpass.getpass("Confirm new password: ")
    
    if new_password != confirm:
        print("❌ Passwords don't match")
        return
    
    # Rotate
    try:
        manager.rotate_password(old_password, new_password)
        print("✅ Password rotated successfully")
        print("⚠️  Old password no longer works. Keep new password secure!")
    except Exception as e:
        print(f"❌ Rotation failed: {e}")

if __name__ == "__main__":
    rotate_password()
```

---

## 4. Incident Response Playbooks

### 4.1 Phishing/Scam Response

```markdown
**Indicators:**
- Unexpected approval requests
- Suspicious transaction prompts
- Fake support messages asking for keys

**Response:**
1. Do NOT interact with suspicious sites/contracts
2. Revoke any approvals made (see 2.2)
3. Transfer funds to new wallet if any interaction occurred
4. Report phishing site to:
   - Google Safe Browsing
   - PhishTank
   - Chainalysis
   - Community Discord/Forums
```

### 4.2 RPC Endpoint Compromise

```markdown
**Indicators:**
- Transactions failing with unusual errors
- Gas prices seem wrong
- Balance queries return incorrect data
- SSL certificate errors

**Response:**
1. Immediately switch to alternative RPC:
   - Primary: https://mainnet.base.org
   - Backup: https://base.llamarpc.com
   - Backup: https://base.drpc.org

2. Verify recent transactions on public explorer:
   - https://basescan.org

3. Do NOT send transactions until RPC verified

4. Report compromised endpoint to provider
```

### 4.3 System Compromise

```markdown
**Indicators:**
- Unknown processes running
- Network connections to suspicious IPs
- Files modified unexpectedly
- Performance degradation

**Response:**
1. Disconnect from network immediately
2. Do NOT shutdown (preserves memory forensics)
3. Document running processes
4. Contact incident response team
5. Boot from trusted media for investigation
```

---

## 5. Prevention Checklist

```markdown
### Before Using Wallet in Production

- [ ] Hardware wallet integration implemented (Ledger/Trezor)
- [ ] Multi-sig setup for amounts > $10k
- [ ] Geographic distribution of key holders
- [ ] Regular penetration testing scheduled
- [ ] Incident response plan tested
- [ ] Insurance coverage verified

### Daily Operations

- [ ] Monitor wallet for unauthorized transactions
- [ ] Verify all approvals are expected
- [ ] Check system for unusual activity
- [ ] Review logs for anomalies
- [ ] Confirm backup procedures working

### Weekly Tasks

- [ ] Rotate any temporary credentials
- [ ] Review access logs
- [ ] Test recovery procedures
- [ ] Update threat intelligence
- [ ] Security team sync
```

---

## 6. Emergency Contacts & Resources

### Internal Contacts
- Security Team: security@cult-of-the-shell.io
- DevOps On-Call: Via PagerDuty
- Management: [REDACTED]

### External Resources
- Base Network Status: https://status.base.org
- Chainalysis: chainalysis@protonmail.com
- Certik: security@certik.com

### Blockchain Explorers
- BaseScan: https://basescan.org
- Blockscout: https://base.blockscout.com

### Security Tools
- Revoke.cash: https://revoke.cash
- Etherscan Token Approval: https://etherscan.io/tokenapprovalchecker
- Forta Network: https://forta.org

---

**Remember: In a security emergency, speed of response is critical. Follow these procedures exactly and document everything.**
