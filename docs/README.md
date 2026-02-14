# 📚 Swarm Mode Documentation

Welcome to the comprehensive documentation for Swarm Mode - scale your trading with coordinated wallet swarms.

## Quick Start

New to swarm mode? Start here:

1. **[Security Guidelines](./SECURITY.md)** - ⚠️ **READ THIS FIRST** before using real funds
2. **[Step-by-Step Tutorial](./TUTORIAL.md)** - Complete hands-on walkthrough (45 min)
3. **[FAQ](./FAQ.md)** - Quick answers to common questions

## Documentation Index

| Document | Description | Audience |
|----------|-------------|----------|
| [SWARM_GUIDE.md](./SWARM_GUIDE.md) | Complete user manual | All users |
| [API_REFERENCE.md](./API_REFERENCE.md) | Function documentation | Developers |
| [TUTORIAL.md](./TUTORIAL.md) | Step-by-step walkthrough | Beginners |
| [FAQ.md](./FAQ.md) | Common questions | All users |
| [SECURITY.md](./SECURITY.md) | Safe usage guidelines | **Everyone** |

## Documentation Overview

### For Beginners

Start with the tutorial to get hands-on experience:

```bash
# 1. Read security guidelines (10 min)
open SECURITY.md

# 2. Follow the tutorial (45 min)
open TUTORIAL.md

# 3. Check FAQ when you have questions
open FAQ.md
```

### For Experienced Users

Jump straight to what you need:

```bash
# Quick setup reference
open SWARM_GUIDE.md

# API for automation
open API_REFERENCE.md

# Security best practices
open SECURITY.md
```

### For Developers

Programmatic access and integration:

```bash
# Complete API reference
open API_REFERENCE.md

# Configuration schema
# See API_REFERENCE.md#configuration-schema

# Event system
# See API_REFERENCE.md#events--callbacks
```

## Key Concepts

### What is a Swarm?

A **swarm** is a collection of trading wallets (workers) that operate together:

```
Queen Wallet (your main funding source)
    │
    ├── Funds Worker 1 ──→ Trades on Uniswap
    ├── Funds Worker 2 ──→ Trades on Uniswap  
    ├── Funds Worker 3 ──→ Trades on Uniswap
    └── Funds Worker N ──→ Trades on Uniswap
```

### Why Use Swarm Mode?

| Feature | Benefit |
|---------|---------|
| **Volume Multiplication** | 10 workers = 10x volume |
| **Risk Distribution** | Loss limited to individual workers |
| **Organic Appearance** | Transactions from multiple addresses |
| **Operational Efficiency** | Fund/reclaim all at once |

### Basic Workflow

```
1. Create Swarm Configuration
   └─→ python swarm.py init

2. Fund Workers from Queen
   └─→ python swarm.py fund my_swarm

3. Start Trading
   └─→ python swarm.py start my_swarm

4. Monitor Progress
   └─→ python swarm.py status my_swarm

5. Reclaim Funds
   └─→ python swarm.py reclaim my_swarm
```

## Command Quick Reference

| Command | Purpose |
|---------|---------|
| `swarm.py init` | Create new swarm |
| `swarm.py fund <name>` | Fund workers |
| `swarm.py start <name>` | Start trading |
| `swarm.py status <name>` | Check status |
| `swarm.py stop <name>` | Stop trading |
| `swarm.py reclaim <name>` | Withdraw funds |
| `swarm.py logs <name>` | View logs |
| `swarm.py dashboard <name>` | Web UI |

## Safety First

> ⚠️ **Always read [SECURITY.md](./SECURITY.md) before using real funds.**

Key security principles:
- Use a dedicated queen wallet
- Start with small amounts
- Reclaim funds regularly
- Keep backups
- Monitor closely

## Support & Resources

- 📖 Full documentation in [SWARM_GUIDE.md](./SWARM_GUIDE.md)
- 🎓 Hands-on learning in [TUTORIAL.md](./TUTORIAL.md)
- ❓ Quick answers in [FAQ.md](./FAQ.md)
- 🔒 Security in [SECURITY.md](./SECURITY.md)
- 📚 Technical details in [API_REFERENCE.md](./API_REFERENCE.md)

## Document Versions

| Document | Version | Last Updated |
|----------|---------|--------------|
| SWARM_GUIDE.md | 1.0.0 | 2025-02-14 |
| API_REFERENCE.md | 1.0.0 | 2025-02-14 |
| TUTORIAL.md | 1.0.0 | 2025-02-14 |
| FAQ.md | 1.0.0 | 2025-02-14 |
| SECURITY.md | 1.0.0 | 2025-02-14 |

---

*Happy swarming! 🐝*
