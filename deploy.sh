#!/bin/bash
# Deployment Script for $COMPUTE Volume Bot
# Usage: ./deploy.sh [server_ip] [remote_user]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BOT_NAME="compute-bot"
DEPLOY_DIR="/opt/compute-bot"
LOCAL_USER=${2:-"root"}
SERVER=${1:-""}

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║        🤖 $COMPUTE Volume Bot - Deployment Script          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if [ ! -f "bot.py" ]; then
        log_error "bot.py not found. Are you in the right directory?"
        exit 1
    fi
    
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt not found"
        exit 1
    fi
    
    log_success "Prerequisites OK"
}

# Create deployment package
create_package() {
    log_info "Creating deployment package..."
    
    DEPLOY_PKG="/tmp/compute-bot-deploy"
    mkdir -p $DEPLOY_PKG
    
    # Copy Python files
    cp *.py $DEPLOY_PKG/
    cp requirements.txt $DEPLOY_PKG/
    cp *.md $DEPLOY_PKG/ 2>/dev/null || true
    cp Makefile $DEPLOY_PKG/ 2>/dev/null || true
    cp Dockerfile $DEPLOY_PKG/ 2>/dev/null || true
    cp example_config.yaml $DEPLOY_PKG/
    cp compute-bot.service $DEPLOY_PKG/
    
    # Create directory structure
    mkdir -p $DEPLOY_PKG/config
    mkdir -p $DEPLOY_PKG/logs
    
    log_success "Package created at $DEPLOY_PKG"
}

# Local deployment
local_deploy() {
    log_info "Starting local deployment..."
    
    create_package
    
    # Create installation directory
    sudo mkdir -p $DEPLOY_DIR
    sudo cp -r /tmp/compute-bot-deploy/* $DEPLOY_DIR/
    
    # Create user if not exists
    if ! id "compute-bot" &>/dev/null; then
        log_info "Creating compute-bot user..."
        sudo useradd -r -s /bin/false compute-bot
    fi
    
    # Set permissions
    sudo chown -R compute-bot:compute-bot $DEPLOY_DIR
    sudo chmod 750 $DEPLOY_DIR
    sudo chmod 700 $DEPLOY_DIR/config
    
    # Create virtual environment
    log_info "Setting up Python virtual environment..."
    cd $DEPLOY_DIR
    sudo -u compute-bot python3 -m venv venv
    sudo -u compute-bot $DEPLOY_DIR/venv/bin/pip install -r requirements.txt
    
    # Create systemd service
    log_info "Installing systemd service..."
    sudo cp $DEPLOY_DIR/compute-bot.service /etc/systemd/system/
    sudo sed -i "s|/opt/compute-bot|$DEPLOY_DIR|g" /etc/systemd/system/compute-bot.service
    sudo systemctl daemon-reload
    
    log_success "Local deployment complete!"
    log_info "Next steps:"
    echo "  1. Copy your config to: $DEPLOY_DIR/config/bot_config.yaml"
    echo "  2. Initialize bot: sudo -u compute-bot $DEPLOY_DIR/venv/bin/python $DEPLOY_DIR/bot.py init"
    echo "  3. Test with: sudo -u compute-bot $DEPLOY_DIR/venv/bin/python $DEPLOY_DIR/bot.py run --dry-run"
    echo "  4. Start service: sudo systemctl start compute-bot"
    echo "  5. Enable auto-start: sudo systemctl enable compute-bot"
}

# Remote deployment
remote_deploy() {
    log_info "Deploying to server: $SERVER..."
    
    create_package
    
    # Create tarball
    tar -czf /tmp/compute-bot.tar.gz -C /tmp/compute-bot-deploy .
    
    # Copy to server
    log_info "Copying files to server..."
    scp /tmp/compute-bot.tar.gz $LOCAL_USER@$SERVER:/tmp/
    scp $0 $LOCAL_USER@$SERVER:/tmp/deploy-local.sh
    
    # Execute deployment on remote server
    log_info "Executing remote deployment..."
    ssh $LOCAL_USER@$SERVER << REMOTE
        cd /tmp
        tar -xzf compute-bot.tar.gz -C /tmp/compute-bot-remote
        cd /tmp/compute-bot-remote
        bash /tmp/deploy-local.sh
REMOTE
    
    log_success "Remote deployment complete!"
    log_info "SSH into your server to complete setup:"
    echo "  ssh $LOCAL_USER@$SERVER"
}

# Docker deployment
docker_deploy() {
    log_info "Building Docker image..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker not installed"
        exit 1
    fi
    
    docker build -t compute-bot:latest .
    
    log_success "Docker image built!"
    log_info "Run with:"
    echo "  docker run -v \$(pwd)/config:/app/config compute-bot:latest"
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS] [SERVER_IP]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -l, --local         Local deployment (default)"
    echo "  -r, --remote IP     Deploy to remote server"
    echo "  -d, --docker        Deploy as Docker container"
    echo "  -u, --user USER     SSH user for remote deployment (default: root)"
    echo ""
    echo "Examples:"
    echo "  $0                  # Local deployment"
    echo "  $0 -r 192.168.1.100 # Deploy to remote server"
    echo "  $0 -d               # Docker deployment"
}

# Main
main() {
    check_prerequisites
    
    # Parse arguments
    case "${1:-local}" in
        -h|--help)
            usage
            exit 0
            ;;
        -l|--local)
            local_deploy
            ;;
        -r|--remote)
            if [ -z "$2" ]; then
                log_error "Server IP required for remote deployment"
                usage
                exit 1
            fi
            SERVER=$2
            remote_deploy
            ;;
        -d|--docker)
            docker_deploy
            ;;
        -u|--user)
            LOCAL_USER=$2
            shift 2
            main "$@"
            ;;
        *)
            # If argument looks like IP, do remote deploy
            if [[ $1 =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                SERVER=$1
                remote_deploy
            else
                log_error "Unknown option: $1"
                usage
                exit 1
            fi
            ;;
    esac
    
    echo ""
    log_success "🦑 Praise Compute! Deployment complete!"
}

# Run main
main "$@"
