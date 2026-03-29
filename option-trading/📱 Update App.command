#!/bin/bash
# =============================================================================
#  UPDATE APP & LAUNCH
#  Double-click to install dependencies (if needed) and start the
#  Expo tunnel. Scan the QR code in Expo Go on your iPhone.
#  (First time: right-click → Open to bypass macOS security prompt)
# =============================================================================

# ── Paths — everything lives inside this folder ───────────────────────────────
PROJ_DIR="$(cd "$(dirname "$0")" && pwd)"
IOS_DIR="$PROJ_DIR/ios-app"

# ── Pretty header ─────────────────────────────────────────────────────────────
clear
echo ""
echo "  ┌─────────────────────────────────────────────┐"
echo "  │   Options Trader App  ·  Update & Launch    │"
echo "  └─────────────────────────────────────────────┘"
echo ""

# ── Sanity check ──────────────────────────────────────────────────────────────
if [ ! -d "$IOS_DIR" ]; then
  echo "  ✗  ios-app folder not found inside:"
  echo "     $PROJ_DIR"
  echo ""
  echo "  Press any key to close…"
  read -rn 1
  exit 1
fi

cd "$IOS_DIR"

# ── Step 1 – Clean install dependencies ──────────────────────────────────────
echo "  [1/2]  Installing app dependencies…"
echo ""
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
if [ $? -ne 0 ]; then
  echo ""
  echo "  ✗  npm install failed. Check the errors above."
  echo "  Press any key to close…"
  read -rn 1
  exit 1
fi
echo ""
echo "  ✓  Dependencies installed"
echo ""

# ── Step 2 – Start Expo tunnel (clear cache) ─────────────────────────────────
echo "  [2/2]  Starting Expo tunnel…"
echo ""
echo "  → Open Expo Go on your iPhone and scan the QR code below."
echo "     The app will load automatically."
echo ""
echo "  (Press Ctrl-C or close this window to stop)"
echo ""

npx expo start --tunnel --clear
