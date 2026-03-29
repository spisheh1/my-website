#!/bin/bash
# =============================================================================
#  Options Trader — AWS EC2 Auto-Setup Script
#  Run this ONCE on a fresh Ubuntu 22.04 or 24.04 EC2 instance:
#
#    chmod +x setup.sh
#    sudo ./setup.sh
#
# =============================================================================
set -e   # stop on any error

echo ""
echo "=============================================="
echo " Options Trader — Server Setup"
echo "=============================================="
echo ""

# ── 1. System updates ─────────────────────────────────────────────────────────
echo "[1/8] Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq

# ── 2. Install Python 3, pip, venv, and nginx ─────────────────────────────────
echo "[2/8] Installing Python, pip, nginx..."
apt-get install -y -qq python3 python3-pip python3-venv nginx curl ufw

# ── 3. Create app user and directory ─────────────────────────────────────────
echo "[3/8] Setting up app directory at /opt/trading..."
mkdir -p /opt/trading
useradd -r -s /bin/false trading 2>/dev/null || true
chown -R trading:trading /opt/trading

# ── 4. Install Python packages (inside a virtualenv) ─────────────────────────
echo "[4/8] Installing Python packages (this takes a minute)..."
python3 -m venv /opt/trading/venv
/opt/trading/venv/bin/pip install --quiet flask yfinance pandas numpy requests
chown -R trading:trading /opt/trading/venv

# ── 5. Generate a random API key ──────────────────────────────────────────────
echo "[5/8] Generating API key..."
API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "TRADING_API_KEY=${API_KEY}" > /opt/trading/.env
chmod 600 /opt/trading/.env
chown trading:trading /opt/trading/.env

echo ""
echo "  ┌─────────────────────────────────────────────────────────┐"
echo "  │  YOUR SECRET API KEY (copy this into your iPhone app):  │"
echo "  │                                                          │"
echo "  │  ${API_KEY}"
echo "  │                                                          │"
echo "  │  Also saved to: /opt/trading/.env                       │"
echo "  └─────────────────────────────────────────────────────────┘"
echo ""

# ── 6. Install systemd service ────────────────────────────────────────────────
echo "[6/8] Installing systemd service..."
cat > /etc/systemd/system/trading.service << 'EOF'
[Unit]
Description=Options Trading Server
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=trading
WorkingDirectory=/opt/trading/scripts
EnvironmentFile=/opt/trading/.env
ExecStart=/opt/trading/venv/bin/python server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=trading

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable trading

# ── 7. Configure nginx ────────────────────────────────────────────────────────
echo "[7/8] Configuring nginx..."
cat > /etc/nginx/sites-available/trading << 'NGINX'
# ──────────────────────────────────────────────────────────────────
#  Options Trading App  —  nginx reverse proxy
#
#  Architecture:
#    Port 80  → nginx (public-facing)
#      /        → (reserved for future real estate website)
#      /trading → options app  (API key required)
#      /api     → options app  (API key required)
#
#  To add your real estate website later, uncomment the
#  "FUTURE REAL ESTATE WEBSITE" block below.
# ──────────────────────────────────────────────────────────────────

# Rate limiting — prevents brute-force key guessing
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;

server {
    listen 80;
    server_name _;          # matches any hostname / bare IP

    # ── Security headers ──────────────────────────────────────────
    add_header X-Frame-Options       "DENY"           always;
    add_header X-Content-Type-Options "nosniff"       always;
    add_header Referrer-Policy       "no-referrer"    always;

    # ── Options trading app (API key required) ────────────────────
    location /api/ {
        limit_req zone=api burst=20 nodelay;

        # Block requests without the correct API key
        if ($http_x_api_key = "") {
            return 401 '{"error":"X-API-Key header required"}';
        }

        proxy_pass         http://127.0.0.1:5001;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-API-Key         $http_x_api_key;

        # Longer timeout for SSE / scan endpoints
        proxy_read_timeout 300s;
        proxy_buffering    off;          # required for SSE streaming
    }

    location /trading/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass         http://127.0.0.1:5001/;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-API-Key $http_x_api_key;
        proxy_read_timeout 300s;
        proxy_buffering    off;
    }

    # ── FUTURE REAL ESTATE WEBSITE ────────────────────────────────
    # When you're ready to add your real estate website, uncomment
    # this block and put your website files in /var/www/realestate/
    #
    # location / {
    #     root   /var/www/realestate;
    #     index  index.html;
    #     try_files $uri $uri/ /index.html;
    # }

    # For now, hide the root path
    location / {
        return 404;
    }
}
NGINX

# Enable the site, disable default
ln -sf /etc/nginx/sites-available/trading /etc/nginx/sites-enabled/trading
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl restart nginx

# ── 8. Configure firewall ─────────────────────────────────────────────────────
echo "[8/8] Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh          # port 22 — for your SSH access
ufw allow http         # port 80 — nginx
ufw allow https        # port 443 — for future SSL
ufw --force enable

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "=============================================="
echo " Setup complete!"
echo "=============================================="
echo ""
echo " Next step: upload your trading scripts"
echo ""
echo "   From your Mac, run:"
echo "   scp -i your-key.pem -r 'option trading/scripts/' ubuntu@YOUR-EC2-IP:/opt/trading/"
echo "   ssh -i your-key.pem ubuntu@YOUR-EC2-IP 'sudo chown -R trading:trading /opt/trading/scripts'"
echo ""
echo " Then start the server:"
echo "   sudo systemctl start trading"
echo "   sudo systemctl status trading"
echo ""
echo " Your API key is saved in /opt/trading/.env"
echo " Show it anytime with: sudo cat /opt/trading/.env"
echo ""
