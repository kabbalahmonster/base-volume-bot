# Deployment Checklist for $COMPUTE Volume Bot

Use this checklist when deploying the bot to production.

## Pre-Deployment

### Environment Setup
- [ ] Python 3.9+ installed
- [ ] Virtual environment created and activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Git repository initialized (excluding config files)

### Wallet Preparation
- [ ] Dedicated wallet created (don't use primary wallet)
- [ ] Wallet has sufficient ETH on Base for gas (~0.1 ETH recommended)
- [ ] Private key backed up securely (offline)
- [ ] Wallet address verified on [BaseScan](https://basescan.org)

### Configuration
- [ ] `python bot.py init` executed successfully
- [ ] RPC URL tested and working
- [ ] All settings reviewed and appropriate:
  - [ ] `buy_amount_eth` (start small: 0.001-0.002)
  - [ ] `buy_interval_seconds` (300 = 5 min is reasonable)
  - [ ] `sell_after_buys` (5-10 is typical)
  - [ ] `max_gas_price_gwei` (2-5 Gwei on Base)
  - [ ] `slippage_percent` (1-3% recommended)
- [ ] Encryption password is strong and backed up
- [ ] Config file has correct permissions (`chmod 600`)

### Testing
- [ ] `python bot.py status` shows valid config
- [ ] `python bot.py wallet-info` shows correct address and balances
- [ ] Dry run completed successfully (`python bot.py run --dry-run`)
- [ ] At least one manual buy tested with small amount
- [ ] Logs are being written to configured location

## Deployment

### Server Setup
- [ ] Server/VPS secured (SSH keys, firewall, updates)
- [ ] Non-root user created for running bot
- [ ] Required ports open (if applicable)
- [ ] Time synchronized (`ntp` or `chrony`)

### Bot Installation
- [ ] Code deployed to server
- [ ] Virtual environment created on server
- [ ] Dependencies installed on server
- [ ] Config file copied securely (SCP/rsync)
- [ ] Config permissions verified (`ls -la bot_config.yaml`)

### Process Management
Choose one:
- [ ] **Systemd service** configured and enabled
- [ ] **PM2** configured and started
- [ ] **Screen/Tmux** session configured
- [ ] **Docker** container built and running

### Monitoring
- [ ] Log rotation configured (logrotate)
- [ ] Health check endpoint/script working
- [ ] Alerting configured (optional: Discord, Telegram, email)
- [ ] Dashboard/monitoring accessible (if applicable)

## Post-Deployment

### Initial Verification
- [ ] Bot started without errors
- [ ] First buy transaction successful
- [ ] Transaction visible on BaseScan
- [ ] Logs show normal operation
- [ ] No error messages in logs

### First Cycle
- [ ] Multiple buys executed successfully
- [ ] Gas costs within expected range
- [ ] No slippage issues
- [ ] Sell executed after target buys
- [ ] Funds returned to ETH

### Ongoing Monitoring
- [ ] Daily log review
- [ ] Weekly balance reconciliation
- [ ] Monthly gas cost analysis
- [ ] Quarterly security review

## Security Hardening

### Server Security
- [ ] SSH key authentication only (no password)
- [ ] Firewall enabled (ufw/iptables)
- [ ] Automatic updates enabled
- [ ] Fail2ban installed
- [ ] Unnecessary services disabled

### Bot Security
- [ ] Config file encrypted and backed up
- [ ] Encryption password not stored on server
- [ ] Logs don't contain sensitive data
- [ ] Private key never in shell history
- [ ] Process runs as non-root user

### Access Control
- [ ] Server access limited to necessary users
- [ ] 2FA enabled where possible
- [ ] Regular password rotation
- [ ] Access logs reviewed periodically

## Backup & Recovery

### Backup Plan
- [ ] Config file backed up securely (encrypted)
- [ ] Private key backed up offline
- [ ] Server snapshots/backups scheduled
- [ ] Recovery procedure documented

### Recovery Testing
- [ ] Test restore from backup
- [ ] Verify bot runs correctly after restore
- [ ] Document recovery time objective (RTO)

## Emergency Procedures

### If Bot Malfunctions
1. Stop bot immediately: `sudo systemctl stop compute-bot` or `pm2 stop compute-bot`
2. Check logs for errors: `tail -n 100 bot.log`
3. Verify wallet status on BaseScan
4. Contact developer/support if needed

### If Wallet Compromised
1. Stop bot immediately
2. Transfer any remaining funds to secure wallet
3. Rotate all keys
4. Review access logs
5. Rebuild server from clean image

### If Server Compromised
1. Stop all processes
2. Isolate server from network
3. Transfer funds from bot wallet
4. Forensic analysis (if required)
5. Rebuild from clean image

## Cost Estimation

### Initial Setup Costs
- Server/VPS: $5-20/month
- Domain (optional): $10-15/year
- Initial ETH for testing: ~$50-100

### Operating Costs (Per Day)
- Server: ~$0.30/day
- Gas costs: ~$0.05-0.20/day (Base is cheap!)
- Total: ~$0.35-0.50/day

### Volume Generation
- Assuming 0.002 ETH buys every 5 minutes
- ~288 buys per day
- Sell every 10 buys = ~29 sell cycles
- Daily volume: ~0.576 ETH (~$1700 at $3000/ETH)

## Troubleshooting Quick Reference

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| "RPC connection failed" | Invalid RPC URL | Check URL, try backup RPC |
| "Gas price too high" | Network congestion | Wait or increase max_gas_price_gwei |
| "Insufficient funds" | Low ETH balance | Add ETH to wallet |
| "Transaction failed" | Slippage or gas | Increase slippage or gas limit |
| "Nonce too low" | Stale nonce | Wait for pending tx or reset nonce |
| "Approval failed" | Token issues | Check token contract, try manual approval |

## Support Contacts

- GitHub Issues: [Repository Issues]
- Documentation: README.md and code comments
- Community: [Discord/Telegram if applicable]

---

**Last Updated**: 2024
**Version**: 1.0.0

Remember: **Test thoroughly before using significant funds!**
