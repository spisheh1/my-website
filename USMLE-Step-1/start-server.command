#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  USMLE Step 1 — Local Server Launcher
#  Double-click this file in Finder to start the app.
#  (If macOS asks "Are you sure?", click Open)
# ─────────────────────────────────────────────────────────────
cd "$(dirname "$0")"

# Kill anything already on 8765
lsof -ti:8765 | xargs kill -9 2>/dev/null
sleep 0.3

echo "╔══════════════════════════════════════╗"
echo "║   USMLE Step 1 — Starting server…   ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "→ Opening http://localhost:8765/step1.html"
echo "→ Keep this window open while studying"
echo "→ Press Ctrl+C here to stop the server"
echo ""

# Open Chrome to the app (tries Chrome first, falls back to default browser)
(sleep 1.2 && open -a "Google Chrome" "http://localhost:8765/step1.html" 2>/dev/null \
  || open "http://localhost:8765/step1.html") &

# Start server — try python3 first, fall back to python
if command -v python3 &>/dev/null; then
  python3 -m http.server 8765
elif command -v python &>/dev/null; then
  python -m SimpleHTTPServer 8765
else
  echo "ERROR: Python not found. Install Python from https://python.org"
  read -p "Press Enter to close..."
fi
