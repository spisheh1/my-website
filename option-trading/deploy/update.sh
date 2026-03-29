#!/bin/bash
# =============================================================================
#  Options Trader — Deploy Update Script
#  Run this from your MAC whenever you update the trading scripts.
#
#  Usage:
#    chmod +x deploy/update.sh
#    ./deploy/update.sh YOUR-EC2-IP your-key.pem
#
#  Example:
#    ./deploy/update.sh 54.123.45.67 ~/Downloads/my-key.pem
# =============================================================================

EC2_IP="${1}"
KEY_FILE="${2:-~/.ssh/id_rsa}"
EC2_USER="ubuntu"
SCRIPTS_DIR="option trading/scripts"

if [ -z "$EC2_IP" ]; then
  echo "Usage: ./deploy/update.sh <EC2-IP> [key-file]"
  echo "Example: ./deploy/update.sh 54.123.45.67 ~/Downloads/trading-key.pem"
  exit 1
fi

echo ""
echo "Deploying to ${EC2_IP}..."
echo ""

# Stop server before upload to avoid file-in-use issues
echo "→ Stopping server..."
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_IP}" \
    "sudo systemctl stop trading 2>/dev/null; echo 'stopped'"

# Upload scripts
echo "→ Uploading scripts..."
scp -i "$KEY_FILE" -o StrictHostKeyChecking=no -r \
    "${SCRIPTS_DIR}/." \
    "${EC2_USER}@${EC2_IP}:/opt/trading/scripts/"

# Fix ownership and restart
echo "→ Restarting server..."
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_IP}" \
    "sudo chown -R trading:trading /opt/trading/scripts && sudo systemctl start trading"

# Show status
echo ""
echo "→ Server status:"
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_IP}" \
    "sudo systemctl status trading --no-pager -l | head -20"

echo ""
echo "✓ Deploy complete!"
echo ""
echo "  Server: http://${EC2_IP}/api/"
echo "  Logs:   ssh -i ${KEY_FILE} ${EC2_USER}@${EC2_IP} 'sudo journalctl -u trading -f'"
echo ""
