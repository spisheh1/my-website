#!/bin/bash
# =============================================================================
#  DEPLOY TO SERVER
#  Double-click this file to push your latest server code to EC2.
#  (First time: right-click → Open to bypass macOS security prompt)
# =============================================================================

# ── Always run from this script's folder ─────────────────────────────────────
cd "$(dirname "$0")"

# ── Pretty header ─────────────────────────────────────────────────────────────
clear
echo ""
echo "  ┌─────────────────────────────────────────────┐"
echo "  │   Options Trader  ·  Deploy to Server       │"
echo "  └─────────────────────────────────────────────┘"
echo ""

# ── Run the deploy script ─────────────────────────────────────────────────────
bash deploy/deploy.sh

# ── Keep window open so you can read the result ───────────────────────────────
echo ""
echo "  Press any key to close this window…"
read -rn 1
