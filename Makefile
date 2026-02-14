.PHONY: help install setup run dry-run balance withdraw test clean lint format

PYTHON := python3
PIP := pip3
BOT := $(PYTHON) bot.py

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	$(PIP) install -r requirements.txt

setup: ## Initialize bot (create encrypted wallet and config)
	$(BOT) setup

run: ## Start the bot
	$(BOT) run

dry-run: ## Start bot in dry-run mode (no real transactions)
	$(BOT) run --dry-run

balance: ## Check wallet balances
	$(BOT) balance

withdraw: ## Withdraw funds (usage: make withdraw ADDR=0x... AMOUNT=0.5)
	@if [ -z "$(ADDR)" ]; then \
		echo "Usage: make withdraw ADDR=0xYourAddress [AMOUNT=0.5] [--compute]"; \
		exit 1; \
	fi
	$(BOT) withdraw $(ADDR) $(if $(AMOUNT),--amount $(AMOUNT),) $(if $(COMPUTE),--compute,)

test: ## Run tests (if any)
	$(PYTHON) -m pytest tests/ -v || echo "No tests yet"

lint: ## Run linter
	$(PYTHON) -m flake8 *.py --ignore=E501,W503 || true
	$(PYTHON) -m pylint *.py --disable=C,R || true

format: ## Format code
	$(PYTHON) -m black *.py || true

clean: ## Clean generated files
	rm -rf __pycache__ *.pyc .pytest_cache *.egg-info build dist
	rm -f *.log
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

venv: ## Create virtual environment
	$(PYTHON) -m venv venv
	@echo "Run 'source venv/bin/activate' to activate"

docker-build: ## Build Docker image
	docker build -t compute-bot .

docker-run: ## Run Docker container (mounts current dir as config)
	docker run -v $(PWD):/app/config compute-bot

backup: ## Backup configuration and wallet
	@mkdir -p backups
	@cp bot_config.json backups/bot_config_$(shell date +%Y%m%d_%H%M%S).json 2>/dev/null || echo "No config to backup"
	@cp .bot_wallet.enc backups/.bot_wallet_$(shell date +%Y%m%d_%H%M%S).enc 2>/dev/null || echo "No wallet to backup"
	@echo "Backup created in backups/"

logs: ## Show recent logs
	tail -n 50 volume_bot.log 2>/dev/null || echo "No log file found"

monitor: ## Monitor logs in real-time
	tail -f volume_bot.log

stop: ## Stop running bot (if using systemd)
	sudo systemctl stop compute-bot 2>/dev/null || echo "Bot not running as service"

restart: ## Restart bot (if using systemd)
	sudo systemctl restart compute-bot 2>/dev/null || echo "Bot not running as service"

update: ## Update bot code and dependencies
	git pull
	$(PIP) install -r requirements.txt
