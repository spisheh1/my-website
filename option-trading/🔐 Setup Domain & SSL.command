#!/bin/bash
# =============================================================================
#  Setup Domain & SSL for spisheh.com
#  - Updates nginx to use your domain name
#  - Installs a free SSL certificate (Let's Encrypt / certbot)
#  - Enables HTTPS with auto-redirect from HTTP
#
#  Run once after deploy. Safe to re-run.
# =============================================================================

cd "$(dirname "$0")"

EC2_IP="54.219.85.193"
KEY_FILE="$HOME/Downloads/trading-key.pem"
EC2_USER="ubuntu"
DOMAIN="spisheh.com"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'

clear
echo ""
echo "  ┌──────────────────────────────────────────────────┐"
echo "  │   Options Trader  ·  Domain & SSL Setup          │"
echo "  │   Domain : spisheh.com                           │"
echo "  │   Server : 54.219.85.193                         │"
echo "  └──────────────────────────────────────────────────┘"
echo ""

# ── Check key file ─────────────────────────────────────────────────────────────
if [ ! -f "$KEY_FILE" ]; then
  echo -e "${RED}✗ Key file not found: $KEY_FILE${NC}"
  echo "  Make sure trading-key.pem is in your Downloads folder."
  echo ""
  echo "  Press any key to close…"
  read -rn 1; exit 1
fi

# ── Step 3: Update nginx with domain name ──────────────────────────────────────
echo -e "${YELLOW}[Step 3/4] Updating nginx config for ${DOMAIN}…${NC}"

ssh -i "$KEY_FILE" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=15 \
    "${EC2_USER}@${EC2_IP}" << 'REMOTE_NGINX'

sudo tee /etc/nginx/sites-enabled/trading > /dev/null << 'NGINXEOF'
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;

server {
    listen 80;
    server_name spisheh.com www.spisheh.com;

    root /var/www/spisheh.com;
    index index.html;

    # Trading dashboard — Flask handles session auth
    location /trading/ {
        proxy_pass http://127.0.0.1:8080/;
        proxy_http_version 1.1;
        proxy_set_header Host       $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Cookie     $http_cookie;
        proxy_cache_bypass 1;
    }

    # API — Flask handles session auth
    location /api/ {
        limit_req zone=api_limit burst=60 nodelay;
        proxy_pass http://127.0.0.1:8080/api/;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_set_header Host       $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Cookie     $http_cookie;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600;
    }

    # Static site (realtor website + step1)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINXEOF

sudo nginx -t && sudo systemctl reload nginx && echo "NGINX_OK"
REMOTE_NGINX

if [ $? -ne 0 ]; then
  echo -e "${RED}✗ nginx update failed. Check your SSH connection.${NC}"
  echo ""; echo "  Press any key to close…"; read -rn 1; exit 1
fi

echo -e "${GREEN}  ✓ nginx updated for ${DOMAIN}${NC}"
echo ""

# ── Step 4: Install certbot + get SSL certificate ──────────────────────────────
echo -e "${YELLOW}[Step 4/4] Installing SSL certificate for ${DOMAIN}…${NC}"
echo -e "  ${CYAN}This may take 1–2 minutes. certbot will verify domain ownership.${NC}"
echo ""

ssh -i "$KEY_FILE" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=30 \
    -o ServerAliveInterval=30 \
    "${EC2_USER}@${EC2_IP}" << 'REMOTE_SSL'

# Install certbot if not already present
if ! command -v certbot &>/dev/null; then
  echo "  Installing certbot…"
  sudo apt-get update -qq
  sudo apt-get install -y -qq certbot python3-certbot-nginx
fi

# Check if certificate already exists
if sudo certbot certificates 2>/dev/null | grep -q "spisheh.com"; then
  echo "  Certificate already exists — renewing if needed…"
  sudo certbot renew --quiet --nginx
  echo "CERT_OK_RENEWED"
else
  # Get new certificate — non-interactive, agree to TOS, no email prompt
  sudo certbot --nginx \
      -d spisheh.com \
      -d www.spisheh.com \
      --non-interactive \
      --agree-tos \
      --register-unsafely-without-email \
      --redirect \
      2>&1
  echo "CERT_OK_NEW"
fi

# Enable auto-renewal (cron job)
sudo systemctl enable certbot.timer 2>/dev/null || true

echo "SSL_SETUP_COMPLETE"
REMOTE_SSL

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${GREEN}  ✓ Domain & SSL setup complete!${NC}"
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo -e "  ${CYAN}Your dashboard is now live at:${NC}"
  echo -e "  ${GREEN}https://spisheh.com/trading/${NC}"
  echo ""
  echo -e "  ${CYAN}HTTP automatically redirects to HTTPS.${NC}"
  echo -e "  ${CYAN}SSL certificate auto-renews every 90 days.${NC}"
else
  echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${RED}  ✗ SSL step had issues.${NC}"
  echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo "  Common causes:"
  echo "  • DNS hasn't propagated yet (wait 10–30 min and retry)"
  echo "  • spisheh.com A record not pointing to 54.219.85.193 yet"
  echo "  • Port 80 blocked by EC2 Security Group"
  echo ""
  echo "  Check DNS at: https://dnschecker.org/#A/spisheh.com"
fi

echo ""
echo "  Press any key to close…"
read -rn 1
