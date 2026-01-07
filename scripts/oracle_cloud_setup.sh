#!/bin/bash
# Oracle Cloud Fish Tank Setup Script
# Run this on your Oracle Cloud instance after SSH-ing in

set -e  # Exit on error

echo "=========================================="
echo "Fish Tank Oracle Cloud Setup Script"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="${REPO_URL:-https://github.com/YOUR_USERNAME/tank.git}"
INSTALL_DIR="/home/ubuntu/tank"
PYTHON_VERSION="3.11"
SERVER_ID="${SERVER_ID:-oracle-fishtank}"
DOMAIN="${DOMAIN:-}"  # Set this if you have a domain

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Don't run this script as root. Run as ubuntu user."
    exit 1
fi

echo ""
echo "Step 1: Updating system packages..."
sudo apt update && sudo apt upgrade -y
print_status "System updated"

echo ""
echo "Step 2: Installing dependencies..."
sudo apt install -y \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python3-pip \
    git \
    nginx \
    certbot \
    python3-certbot-nginx \
    htop \
    fail2ban \
    ufw
print_status "Dependencies installed"

echo ""
echo "Step 3: Installing Node.js..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
fi
print_status "Node.js $(node --version) installed"

echo ""
echo "Step 4: Configuring firewall..."
# Oracle Cloud uses iptables by default
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT 2>/dev/null || true

# Also setup UFW as backup
sudo ufw default deny incoming 2>/dev/null || true
sudo ufw default allow outgoing 2>/dev/null || true
sudo ufw allow ssh 2>/dev/null || true
sudo ufw allow 80/tcp 2>/dev/null || true
sudo ufw allow 443/tcp 2>/dev/null || true
echo "y" | sudo ufw enable 2>/dev/null || true

# Save iptables rules
sudo netfilter-persistent save 2>/dev/null || true
print_status "Firewall configured"

echo ""
echo "Step 5: Cloning/updating repository..."
if [ -d "$INSTALL_DIR" ]; then
    print_warning "Directory exists, pulling latest changes..."
    cd "$INSTALL_DIR"
    git pull
else
    print_warning "Please clone your repository manually:"
    echo "  git clone $REPO_URL $INSTALL_DIR"
    echo ""
    echo "Then re-run this script."
    exit 1
fi
print_status "Repository ready"

echo ""
echo "Step 6: Setting up Python environment..."
cd "$INSTALL_DIR"
if [ ! -d "venv" ]; then
    python${PYTHON_VERSION} -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -e .
pip install psutil slowapi  # Production extras
print_status "Python environment ready"

echo ""
echo "Step 7: Creating systemd service..."
sudo tee /etc/systemd/system/fishtank.service > /dev/null << EOF
[Unit]
Description=Fish Tank Simulation Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=${INSTALL_DIR}
Environment=PATH=${INSTALL_DIR}/venv/bin:/usr/bin
Environment=PYTHONUNBUFFERED=1
Environment=TANK_SERVER_ID=${SERVER_ID}
ExecStart=${INSTALL_DIR}/venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable fishtank
print_status "Systemd service created"

echo ""
echo "Step 8: Configuring Nginx..."
NGINX_SERVER_NAME="${DOMAIN:-_}"
sudo tee /etc/nginx/sites-available/fishtank > /dev/null << EOF
limit_req_zone \$binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_conn_zone \$binary_remote_addr zone=conn_limit:10m;

server {
    listen 80;
    server_name ${NGINX_SERVER_NAME};

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        limit_conn conn_limit 10;

        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/fishtank /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
print_status "Nginx configured"

echo ""
echo "Step 9: Starting Fish Tank service..."
sudo systemctl start fishtank
sleep 3

if sudo systemctl is-active --quiet fishtank; then
    print_status "Fish Tank service is running!"
else
    print_error "Fish Tank service failed to start. Check logs:"
    echo "  sudo journalctl -u fishtank -n 50"
    exit 1
fi

echo ""
echo "Step 10: Enabling fail2ban..."
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
print_status "Fail2ban enabled"

echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Your Fish Tank server is now running!"
echo ""
echo "Access your server:"
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_PUBLIC_IP")
echo "  http://${PUBLIC_IP}/"
echo "  http://${PUBLIC_IP}/health"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status fishtank    # Check status"
echo "  sudo journalctl -u fishtank -f    # View logs"
echo "  sudo systemctl restart fishtank   # Restart"
echo ""

if [ -z "$DOMAIN" ]; then
    echo -e "${YELLOW}SSL Setup:${NC}"
    echo "If you have a domain, run:"
    echo "  sudo certbot --nginx -d your-domain.com"
    echo ""
fi

echo "Done! 🐟"
