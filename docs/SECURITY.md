# 🔒 Swarm Mode - Security Guidelines

**Read this document carefully before using swarm mode with real funds.**

> ⚠️ **WARNING:** Swarm mode involves managing multiple wallets and private keys. Mistakes can result in **permanent loss of funds**. This is experimental software. Use at your own risk.

---

## Table of Contents

1. [Security Checklist](#security-checklist)
2. [Understanding the Risks](#understanding-the-risks)
3. [Queen Wallet Security](#queen-wallet-security)
4. [Worker Wallet Security](#worker-wallet-security)
5. [Operational Security](#operational-security)
6. [Network Security](#network-security)
7. [Emergency Procedures](#emergency-procedures)
8. [Best Practices](#best-practices)
9. [Common Attacks & Mitigations](#common-attacks--mitigations)
10. [Incident Response](#incident-response)

---

## Security Checklist

### Before Creating Your First Swarm

- [ ] Read this entire document
- [ ] Read the [Swarm Guide](./SWARM_GUIDE.md)
- [ ] Completed the [Tutorial](./TUTORIAL.md) with test amounts
- [ ] Understand all risks involved
- [ ] Using a dedicated queen wallet (not your main wallet)
- [ ] Have a backup of your encryption password
- [ ] Server/machine is secure and updated
- [ ] Firewall enabled
- [ ] No malware detected

### Before Running Production Swarm

- [ ] Tested with small amounts (< $50)
- [ ] Verified reclaim process works
- [ ] Set up monitoring and alerts
- [ ] Configured automatic loss limits
- [ ] Documented configuration
- [ ] Have recovery plan
- [ ] Scheduled regular reclaims
- [ ] Backed up all configuration files

### Ongoing Security

- [ ] Monitor swarm daily
- [ ] Review logs weekly
- [ ] Reclaim funds regularly
- [ ] Update software monthly
- [ ] Review access logs
- [ ] Test restore from backup quarterly

---

## Understanding the Risks

### Financial Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Loss of private keys | Low | Critical | Backups, password manager |
| Smart contract bugs | Low | High | Test with small amounts |
| Gas price spikes | Medium | Medium | Set max gas limits |
| Slippage losses | Medium | Medium | Set slippage limits |
| Market volatility | High | Variable | Diversify, limit exposure |

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Software bugs | Medium | High | Test thoroughly |
| RPC failures | Medium | Medium | Use multiple RPCs |
| Network issues | Medium | Low | Retry logic |
| Data corruption | Low | High | Regular backups |

### Security Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Server compromise | Low | Critical | Secure server, monitoring |
| Password theft | Low | Critical | Strong passwords, 2FA |
| Social engineering | Medium | Critical | Education, procedures |
| Supply chain attack | Very Low | Critical | Verify dependencies |

---

## Queen Wallet Security

The **queen wallet** is your most critical asset. It controls all worker funding and reclaims.

### Queen Wallet Best Practices

#### 1. Use a Dedicated Wallet

```
❌ DON'T: Use your main wallet
❌ DON'T: Use a wallet with other funds
✅ DO: Create a wallet specifically for swarm operations
```

**To create a dedicated queen wallet:**

```bash
# Option 1: Create new wallet
# Use MetaMask, Rabby, or other wallet software
# Send only the amount needed for operations

# Option 2: Hardware wallet (recommended for large amounts)
# Ledger, Trezor, etc.
# Keep device offline except when funding/reclaiming
```

#### 2. Limit Queen Wallet Balance

**Never keep more than needed in the queen wallet:**

```
Recommended maximums:
- Test swarms: 0.05 ETH
- Small production: 0.5 ETH
- Large production: 2.0 ETH
```

**Calculate required amount:**

```bash
# Workers × (Funding + Gas Reserve) × Safety Factor
# Example: 10 workers × 0.015 ETH × 1.5 = 0.225 ETH needed
```

#### 3. Secure the Configuration

The queen wallet configuration contains your encrypted private key:

```bash
# Set restrictive permissions
chmod 600 bot_config.yaml

# Never commit to git
echo "bot_config.yaml" >> .gitignore
echo "swarm_configs/" >> .gitignore

# Store in encrypted location
# - Encrypted USB drive
# - Password manager secure notes
# - Hardware security module
```

#### 4. Use Hardware Wallet for Large Amounts

**For queen wallets holding > 1 ETH:**

```
Setup:
1. Create wallet on hardware device
2. Export address (not private key)
3. Configure swarm to use this address
4. Sign funding/reclaim transactions manually
5. Keep device in safe when not in use
```

---

## Worker Wallet Security

Workers are created and managed by the swarm system.

### Worker Wallet Security Model

```
┌─────────────────────────────────────────────────────────┐
│                    SECURITY HIERARCHY                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  CRITICAL: Queen Wallet                                 │
│  ├── Controls all funds                                 │
│  ├── Can drain all workers                              │
│  └── Keep most secure                                   │
│                                                         │
│  HIGH: Encryption Password                              │
│  ├── Protects all worker keys                           │
│  ├── Loss = worker funds lost                           │
│  └── Store in password manager                          │
│                                                         │
│  MEDIUM: Worker Wallet Files                            │
│  ├── Encrypted private keys                             │
│  ├── Need password to decrypt                           │
│  └── Limit exposure                                     │
│                                                         │
│  LOW: Individual Worker Balances                        │
│  ├── Limited funds                                      │
│  ├── Can be reclaimed                                   │
│  └── Acceptable risk                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Worker Encryption

All worker private keys are encrypted using:
- **Algorithm:** Fernet (AES-128-CBC)
- **Key Derivation:** PBKDF2 with 480,000 iterations
- **Salt:** Random 16 bytes per worker

```
Encryption Flow:

Your Password + Salt ──→ PBKDF2 ──→ Encryption Key ──→ Encrypt Private Key
                                                              ↓
                                                   swarm_configs/<name>/workers/
                                                              ↓
Your Password + Salt ──→ PBKDF2 ──→ Encryption Key ──→ Decrypt at Runtime
```

### Protecting Worker Files

```bash
# Set proper permissions
chmod 700 swarm_configs/
chmod 600 swarm_configs/*/
chmod 600 swarm_configs/*/workers/*.enc

# Verify permissions
ls -la swarm_configs/
# Should show: drwx------ for directories, -rw------- for files
```

### Password Best Practices

```
❌ DON'T:
- Use simple passwords (password123)
- Reuse passwords from other accounts
- Store in plain text files
- Share with others
- Use short passwords (< 16 characters)

✅ DO:
- Use password manager (1Password, Bitwarden, etc.)
- Generate random passwords (32+ characters)
- Enable 2FA on password manager
- Write down and store in physical safe
- Test password recovery process
```

**Example strong password:**
```
k9#mP2$vL8@nQ5&wR7*fJ4!hT6%cX3
```

---

## Operational Security

### Server Security

#### Minimum Requirements

```bash
# 1. Keep system updated
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
sudo yum update -y                       # RHEL/CentOS

# 2. Configure firewall
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8080/tcp  # If using dashboard

# 3. Disable password auth (use SSH keys only)
# Edit /etc/ssh/sshd_config
PasswordAuthentication no
PubkeyAuthentication yes

# 4. Install and configure fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

#### Running as Non-Root User

```bash
# Create dedicated user
sudo useradd -m -s /bin/bash swarmbot
sudo usermod -aG sudo swarmbot

# Set up swarm in user directory
sudo su - swarmbot
cd ~
# Copy swarm_configs here

# Run as this user only
python swarm.py start my_swarm
```

#### File Permissions

```bash
# Recommended ownership
sudo chown -R swarmbot:swarmbot swarm_configs/
sudo chmod -R 700 swarm_configs/

# Verify
find swarm_configs/ -type f -ls
# Should show: -rw------- swarmbot swarmbot
```

### Process Security

#### Running as Service

```ini
# /etc/systemd/system/swarm-bot.service
[Unit]
Description=Swarm Trading Bot
After=network.target

[Service]
Type=simple
User=swarmbot
Group=swarmbot
WorkingDirectory=/home/swarmbot/volume_bot
Environment="PYTHONUNBUFFERED=1"
Environment="SWARM_LOG_LEVEL=INFO"
ExecStart=/home/swarmbot/volume_bot/venv/bin/python swarm.py start my_swarm
ExecStop=/home/swarmbot/volume_bot/venv/bin/python swarm.py stop my_swarm
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/swarmbot/volume_bot/swarm_configs

[Install]
WantedBy=multi-user.target
```

#### Container Security (Docker)

```dockerfile
# Use non-root user
FROM python:3.11-slim

# Create user
RUN useradd -m -u 1000 swarmbot

# Install dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=swarmbot:swarmbot . .

# Switch to non-root
USER swarmbot

# Mount config as volume (don't copy secrets)
VOLUME ["/app/swarm_configs"]

CMD ["python", "swarm.py", "start", "my_swarm"]
```

### Log Security

```bash
# Logs may contain sensitive data
# Protect them properly

chmod 600 swarm_configs/*/logs/*.log

# Rotate logs to prevent disk fill
# /etc/logrotate.d/swarm-bot
/home/swarmbot/volume_bot/swarm_configs/*/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0600 swarmbot swarmbot
}
```

---

## Network Security

### RPC Endpoint Security

```
❌ DON'T:
- Use public RPCs for large amounts
- Share your RPC endpoint publicly
- Use HTTP when HTTPS available
- Hardcode API keys in configs

✅ DO:
- Use private/paid RPCs for production
- Rotate API keys regularly
- Monitor RPC usage
- Use multiple fallback RPCs
```

**Recommended RPC Providers:**

| Provider | Privacy | Cost | Reliability |
|----------|---------|------|-------------|
| Alchemy | Good | Paid | Excellent |
| Infura | Good | Freemium | Excellent |
| QuickNode | Good | Paid | Excellent |
| Public RPCs | Poor | Free | Variable |

### Secure Configuration

```yaml
# swarm.yaml - Network section
network:
  # Primary RPC (private endpoint recommended)
  rpc_url: "https://base-mainnet.g.alchemy.com/v2/YOUR_API_KEY"
  
  # Fallback RPCs
  fallback_rpc_urls:
    - "https://mainnet.base.org"
    - "https://base.llamarpc.com"
  
  # Never expose API keys in logs
  mask_rpc_urls: true
```

### Firewall Rules

```bash
# Only allow necessary outbound connections
# Swarm needs: RPC endpoint, optional: Telegram API, Webhook

# Example: Allow only specific outbound
sudo ufw default deny outgoing
sudo ufw allow out to <RPC_IP> port 443  # HTTPS
sudo ufw allow out 53                      # DNS
sudo ufw allow out 123                     # NTP
```

---

## Emergency Procedures

### Emergency Stop

```bash
# Immediate stop (may leave funds in workers)
python swarm.py stop my_swarm --force

# Then reclaim
python swarm.py reclaim my_swarm
```

### If You Suspect Compromise

```
1. STOP EVERYTHING IMMEDIATELY
   python swarm.py stop my_swarm --force

2. RECLAIM FUNDS (if safe to do so)
   python swarm.py reclaim my_swarm

3. DISCONNECT FROM NETWORK
   sudo systemctl stop network
   # OR physically disconnect

4. ASSESS THE DAMAGE
   - Check queen wallet balance
   - Check worker balances
   - Review access logs
   - Check for malware

5. SECURE REMAINING FUNDS
   - Transfer to cold storage
   - Use hardware wallet
   - Multiple signatures if available

6. INVESTIGATE
   - How was access gained?
   - What data was exposed?
   - Who had access?

7. REBUILD SECURELY
   - New server (or wiped old one)
   - New queen wallet
   - New swarm configuration
   - Stronger security measures
```

### If You Lose Your Password

```
⚠️ CRITICAL: Worker funds are LOST

Recovery options:
1. Check password manager history
2. Check written backups
3. Check browser saved passwords
4. Try common variations

If none work:
- Worker funds are permanently inaccessible
- Create new swarm with new password
- Fund with queen wallet
- Learn from mistake: better backup procedures
```

### If Queen Wallet is Compromised

```
1. EMERGENCY RECLAIM (if possible)
   python swarm.py reclaim my_swarm

2. TRANSFER ALL FUNDS to new secure wallet
   # Use hardware wallet or fresh MetaMask

3. CREATE NEW QUEEN WALLET
   # New private key, new address

4. REINITIALIZE SWARM
   python swarm.py init --name my_swarm_v2
   python swarm.py fund my_swarm_v2
   python swarm.py start my_swarm_v2

5. DESTROY OLD CONFIGURATION
   rm -rf swarm_configs/my_swarm/
   shred -u bot_config.yaml.old
```

---

## Best Practices

### The Principle of Least Privilege

```
✅ Workers only have trading funds (not your savings)
✅ Queen only has operational funds (not your entire portfolio)
✅ Server only has swarm access (not your email, etc.)
✅ Password only unlocks workers (use different password for queen)
```

### Regular Reclaim Schedule

```
Recommended reclaim frequency:

| Swarm Size | Reclaim Every |
|------------|---------------|
| < 5 workers | 12-24 hours |
| 5-20 workers | 6-12 hours |
| 20-50 workers | 4-8 hours |
| > 50 workers | 2-4 hours |

Why? Limits exposure if something goes wrong.
```

### Testing Changes

```
Always test with dry-run first:

1. Make configuration change
2. Test in dry-run mode
   python swarm.py start my_swarm --dry-run
3. Verify behavior is expected
4. Stop dry-run
5. Run with real funds (small amount)
6. Monitor closely
7. Scale up gradually
```

### Backup Strategy

```bash
# 1. Regular automated backups
# crontab -e
0 */6 * * * /home/swarmbot/backup_swarm.sh

# 2. Backup script (backup_swarm.sh)
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/secure/backups/swarm"
mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/swarm_backup_$DATE.tar.gz \
  /home/swarmbot/volume_bot/swarm_configs/
# Keep only last 10 backups
ls -t $BACKUP_DIR/swarm_backup_*.tar.gz | tail -n +11 | xargs rm -f

# 3. Offsite backup
# Sync to encrypted cloud storage
rclone sync /secure/backups/swarm encrypted-remote:swarm-backups
```

### Monitoring for Security

```bash
# Watch for suspicious activity

# 1. Check for failed logins
sudo grep "Failed password" /var/log/auth.log

# 2. Monitor swarm processes
ps aux | grep swarm

# 3. Check network connections
sudo netstat -tuln | grep :8080  # Dashboard port

# 4. Review file changes
find swarm_configs/ -mtime -1 -ls

# 5. Monitor large transactions
python swarm.py stats my_swarm --check-anomalies
```

---

## Common Attacks & Mitigations

### 1. Phishing Attacks

**Attack:** Fake website/app asks for private key or password

**Mitigation:**
```
✅ Never enter private key on any website
✅ Never share encryption password
✅ Only use official swarm.py CLI
✅ Verify URLs carefully
✅ Bookmark official documentation
```

### 2. Malware/Keyloggers

**Attack:** Malware steals passwords or private keys

**Mitigation:**
```
✅ Run on dedicated, clean machine
✅ Use hardware wallet for queen
✅ Regular malware scans
✅ Don't browse web on trading server
✅ Keep software updated
```

### 3. Social Engineering

**Attack:** Someone tricks you into revealing secrets

**Mitigation:**
```
✅ No one needs your private keys
✅ No one needs your encryption password
✅ Verify identities through multiple channels
✅ Establish secure communication procedures
✅ Be suspicious of urgent requests
```

### 4. RPC Endpoint Attacks

**Attack:** Malicious RPC returns false data

**Mitigation:**
```
✅ Use reputable RPC providers
✅ Verify transactions independently
✅ Use multiple RPCs as fallback
✅ Check balances on block explorer
```

### 5. Smart Contract Exploits

**Attack:** Vulnerability in Uniswap or token contract

**Mitigation:**
```
✅ Only trade established tokens
✅ Limit exposure per worker
✅ Regular reclaims limit damage
✅ Monitor for unusual activity
```

---

## Incident Response

### Security Incident Response Plan

```
1. DETECTION
   - Monitoring alert
   - Unexpected balance change
   - Failed authentication
   - Suspicious network activity

2. CONTAINMENT
   - Stop all trading
   - Disconnect from network
   - Preserve logs
   - Document timeline

3. ERADICATION
   - Identify root cause
   - Remove malware/backdoors
   - Patch vulnerabilities
   - Rotate all credentials

4. RECOVERY
   - Restore from clean backup
   - Verify integrity
   - Test thoroughly
   - Gradual restart

5. LESSONS LEARNED
   - Document incident
   - Update procedures
   - Improve monitoring
   - Train team
```

### Reporting Security Issues

If you discover a security vulnerability:

```
1. DO NOT disclose publicly
2. Document the issue
3. Contact maintainers privately
4. Allow time for fix
5. Coordinate disclosure
```

---

## Security Checklist for Production

### Pre-Deployment

- [ ] Security audit of configuration
- [ ] Tested reclaim process 3+ times
- [ ] Verified all backups work
- [ ] Documented emergency procedures
- [ ] Set up monitoring and alerting
- [ ] Configured automatic loss limits
- [ ] Limited queen wallet balance
- [ ] Secured server (firewall, updates)
- [ ] Non-root user configured
- [ ] File permissions set correctly

### Deployment

- [ ] Start with dry-run mode
- [ ] Verify all workers connect
- [ ] Check first few transactions
- [ ] Monitor for 1 hour continuously
- [ ] Verify reclaim works
- [ ] Gradually increase size

### Ongoing

- [ ] Daily balance checks
- [ ] Weekly log review
- [ ] Monthly security updates
- [ ] Quarterly backup restore test
- [ ] Annual security review

---

## Final Reminders

> 🔐 **Your security is your responsibility**

1. **Never invest more than you can afford to lose**
2. **Test thoroughly before using real funds**
3. **Keep backups of everything**
4. **Monitor regularly**
5. **Have an exit plan**

> ⚠️ **This software is experimental. No guarantees are provided.**

---

## Resources

- [Swarm Guide](./SWARM_GUIDE.md) - Complete documentation
- [Tutorial](./TUTORIAL.md) - Step-by-step learning
- [FAQ](./FAQ.md) - Common questions
- [API Reference](./API_REFERENCE.md) - Technical details

---

*Stay safe. Trade smart. 🛡️*

*Last updated: 2025-02-14*
