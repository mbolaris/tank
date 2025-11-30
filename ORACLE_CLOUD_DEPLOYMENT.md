# Deploying Fish Tank to Oracle Cloud Always Free

This guide walks you through deploying your Fish Tank simulation to Oracle Cloud's Always Free tier.

## Oracle Cloud Always Free Resources

You get **permanently free**:
- **2 AMD VMs** (1 OCPU, 1GB RAM each) OR
- **4 ARM VMs** (up to 24GB RAM total, 4 OCPUs total) - **Recommended**
- 200GB block storage
- 10TB outbound data/month

## Quick Start (Recommended: ARM Instance)

### Step 1: Create Oracle Cloud Account

1. Go to [cloud.oracle.com](https://cloud.oracle.com)
2. Click "Start for free"
3. Complete registration (requires credit card for verification, but won't charge for Always Free)
4. Wait for account activation (~30 minutes)

### Step 2: Create an ARM Compute Instance

1. Go to **Compute → Instances → Create Instance**
2. Configure:
   - **Name**: `fishtank-server`
   - **Image**: Ubuntu 22.04 (or 24.04)
   - **Shape**: Click "Change Shape"
     - Select **Ampere** (ARM)
     - Choose **VM.Standard.A1.Flex**
     - **OCPUs**: 2 (or up to 4)
     - **Memory**: 12GB (or up to 24GB)
   - **Networking**: Create new VCN or use existing
   - **Add SSH keys**: Upload your public key or generate new

3. Click **Create**

### Step 3: Configure Security (Firewall)

1. Go to **Networking → Virtual Cloud Networks**
2. Click your VCN → **Security Lists** → Default Security List
3. Add **Ingress Rules**:

| Source CIDR | Protocol | Dest Port | Description |
|-------------|----------|-----------|-------------|
| 0.0.0.0/0 | TCP | 80 | HTTP |
| 0.0.0.0/0 | TCP | 443 | HTTPS |
| 0.0.0.0/0 | TCP | 8000 | API (optional, use reverse proxy) |

### Step 4: Connect to Your Instance

```bash
# Get public IP from Oracle Console
ssh -i your-private-key ubuntu@<PUBLIC_IP>
```

### Step 5: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+ and dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx certbot python3-certbot-nginx

# Install Node.js (for frontend)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Open firewall ports (Ubuntu uses iptables by default on Oracle)
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo netfilter-persistent save
```

### Step 6: Clone and Setup Project

```bash
# Clone your repository
cd ~
git clone https://github.com/YOUR_USERNAME/tank.git
cd tank

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -e .
pip install psutil  # For server stats

# Build frontend (if needed)
cd frontend
npm install
npm run build
cd ..
```

### Step 7: Create Systemd Service

```bash
sudo nano /etc/systemd/system/fishtank.service
```

Paste this content:

```ini
[Unit]
Description=Fish Tank Simulation Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/tank
Environment=PATH=/home/ubuntu/tank/venv/bin:/usr/bin
Environment=PYTHONUNBUFFERED=1
Environment=TANK_SERVER_ID=oracle-fishtank
ExecStart=/home/ubuntu/tank/venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable fishtank
sudo systemctl start fishtank

# Check status
sudo systemctl status fishtank

# View logs
sudo journalctl -u fishtank -f
```

### Step 8: Setup Nginx Reverse Proxy with SSL

```bash
sudo nano /etc/nginx/sites-available/fishtank
```

Paste (replace `YOUR_DOMAIN` or use IP):

```nginx
# Rate limiting zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # API endpoints with rate limiting
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        limit_conn conn_limit 10;
        
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket endpoint
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # WebSocket timeouts
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # Health check (no rate limit)
    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # Root endpoint
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/fishtank /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default
sudo nginx -t  # Test config
sudo systemctl restart nginx
```

### Step 9: Add SSL with Let's Encrypt (Optional but Recommended)

If you have a domain pointing to your server:

```bash
sudo certbot --nginx -d your-domain.com
```

Certbot will automatically configure SSL and set up auto-renewal.

---

## Security Hardening Checklist

### 1. Update CORS in Backend

Edit `backend/main.py` to restrict CORS:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-domain.com",
        "http://localhost:3000",  # For local development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### 2. Add API Rate Limiting (Python)

Install and configure:

```bash
pip install slowapi
```

Add to `backend/main.py`:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Then decorate endpoints:
@app.get("/api/tanks")
@limiter.limit("30/minute")
async def get_tanks(request: Request):
    ...
```

### 3. Environment Variables

Create `/home/ubuntu/tank/.env`:

```bash
TANK_SERVER_ID=oracle-fishtank-prod
# Add any secrets here
```

Update systemd service to load it:

```ini
EnvironmentFile=/home/ubuntu/tank/.env
```

### 4. Firewall (UFW Alternative)

```bash
sudo apt install ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 5. Fail2ban (SSH Protection)

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## Monitoring & Maintenance

### View Logs

```bash
# Application logs
sudo journalctl -u fishtank -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Resource Monitoring

```bash
# Real-time stats
htop

# Memory usage
free -h

# Disk usage
df -h
```

### Update Application

```bash
cd ~/tank
git pull
source venv/bin/activate
pip install -e .
sudo systemctl restart fishtank
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u fishtank -n 50

# Test manually
cd ~/tank
source venv/bin/activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Can't Connect from Internet

1. Check Oracle Security List rules (Step 3)
2. Check iptables: `sudo iptables -L -n`
3. Check nginx is running: `sudo systemctl status nginx`
4. Check the app is running: `curl http://localhost:8000/health`

### WebSocket Connection Drops

- Ensure nginx proxy timeouts are long enough
- Check if firewall is blocking persistent connections

---

## Cost Summary

| Resource | Always Free Limit | Your Usage |
|----------|-------------------|------------|
| ARM Compute | 4 OCPUs, 24GB RAM | 2 OCPUs, 12GB |
| Block Storage | 200GB | ~20GB |
| Outbound Data | 10TB/month | Varies |

**Total Cost: $0/month** ✅

---

## Quick Commands Reference

```bash
# Start/Stop/Restart
sudo systemctl start fishtank
sudo systemctl stop fishtank
sudo systemctl restart fishtank

# View status
sudo systemctl status fishtank

# View logs (live)
sudo journalctl -u fishtank -f

# Check if port is open
curl http://localhost:8000/health

# Test from outside
curl http://YOUR_PUBLIC_IP:8000/health
```
