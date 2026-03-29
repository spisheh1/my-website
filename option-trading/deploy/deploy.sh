#!/bin/bash
# =============================================================================
#  Options Trader — One-Command Deploy
#  Pushes all script changes to EC2 and restarts the server.
#
#  Usage (from the "option trading" folder):
#    ./deploy/deploy.sh
# =============================================================================

# ── Your server details (pre-filled) ─────────────────────────────────────────
EC2_IP="54.219.85.193"
KEY_FILE="$HOME/Downloads/trading-key.pem"
EC2_USER="ubuntu"

# ── Resolve the scripts folder relative to this script ───────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
SCRIPTS_DIR="$ROOT_DIR/scripts"

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  Options Trader — Deploying to EC2${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check key file exists
if [ ! -f "$KEY_FILE" ]; then
  echo -e "${RED}✗ Key file not found: $KEY_FILE${NC}"
  echo "  Edit deploy/deploy.sh and set KEY_FILE to your .pem path."
  exit 1
fi

echo -e "  Server : ${EC2_IP}"
echo -e "  Scripts: ${SCRIPTS_DIR}"
echo ""

# ── 1. Upload scripts (stop is NOT needed — we do a hot swap) ─────────────────
echo -e "${YELLOW}[1/3] Uploading scripts...${NC}"

# Ensure the staging folder exists on EC2
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    "${EC2_USER}@${EC2_IP}" "mkdir -p /home/ubuntu/scripts_upload"

scp -i "$KEY_FILE" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 \
    -r "$SCRIPTS_DIR/." \
    "${EC2_USER}@${EC2_IP}:/home/ubuntu/scripts_upload/"

if [ $? -ne 0 ]; then
  echo -e "${RED}✗ Upload failed. Check your connection and key file.${NC}"
  exit 1
fi

# ── 2. Move files into place and restart ──────────────────────────────────────
echo -e "${YELLOW}[2/3] Installing and restarting server...${NC}"
ssh -i "$KEY_FILE" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 \
    "${EC2_USER}@${EC2_IP}" << 'REMOTE'
sudo cp -r /home/ubuntu/scripts_upload/. /opt/trading/scripts/
sudo chown -R trading:trading /opt/trading/scripts/
sudo systemctl restart trading
REMOTE

if [ $? -ne 0 ]; then
  echo -e "${RED}✗ Remote install failed.${NC}"
  exit 1
fi

# ── 3. Wait a moment and show status ──────────────────────────────────────────
echo -e "${YELLOW}[3/3] Checking server status...${NC}"
sleep 3
STATUS=$(ssh -i "$KEY_FILE" \
    -o StrictHostKeyChecking=no \
    "${EC2_USER}@${EC2_IP}" \
    "sudo systemctl is-active trading")

if [ "$STATUS" = "active" ]; then
  echo ""
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${GREEN}  ✓ Deploy complete — server is running!${NC}"
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
else
  echo ""
  echo -e "${RED}  ✗ Server didn't start. Showing logs:${NC}"
  ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_IP}" \
      "sudo journalctl -u trading -n 20 --no-pager"
fi

# ── 4. Git: commit and push changes to GitHub ─────────────────────────────────
REPO_ROOT="$(dirname "$ROOT_DIR")"
TOKEN_FILE="$REPO_ROOT/.git-token"

if [ -d "$REPO_ROOT/.git" ]; then
  echo ""
  echo -e "${YELLOW}[4/4] Syncing to GitHub…${NC}"

  cd "$REPO_ROOT"

  # Load stored token into the remote URL so push works non-interactively
  if [ -f "$TOKEN_FILE" ]; then
    GITHUB_TOKEN=$(cat "$TOKEN_FILE")
    git remote set-url origin "https://spisheh1:${GITHUB_TOKEN}@github.com/spisheh1/my-website.git"
  fi

  # Stage all changes inside the option-trading folder
  git add "$(basename "$ROOT_DIR")/"

  # Only commit if there are staged changes
  CHANGES=$(git diff --staged --name-only 2>/dev/null | wc -l | tr -d ' ')
  if [ "$CHANGES" -gt "0" ]; then
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
    git commit -m "Deploy: ${TIMESTAMP} — ${CHANGES} file(s) updated"

    if git push origin main 2>&1; then
      echo -e "${GREEN}  ✓ Pushed ${CHANGES} file(s) to github.com/spisheh1/my-website${NC}"
    else
      echo -e "${YELLOW}  ⚠ GitHub push failed — run '🔗 Setup GitHub Sync' first${NC}"
    fi
  else
    echo -e "  No code changes since last push — GitHub already up to date"
  fi

  cd "$ROOT_DIR"
else
  echo ""
  echo -e "  ${YELLOW}ℹ GitHub sync not set up — run '🔗 Setup GitHub Sync.command' once to enable${NC}"
fi

echo ""
