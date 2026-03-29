#!/bin/bash
# ============================================================
#  Options Trading Dashboard — Auto Launcher
#  Double-click this file to start the app
# ============================================================

# Get the directory where this script lives
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"

echo ""
echo "============================================================"
echo "   📈 OPTIONS TRADING DASHBOARD"
echo "============================================================"
echo ""

# ── Step 1: Check Python ──────────────────────────────────────
echo "🔍 Checking Python..."
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo ""
    echo "❌ Python not found!"
    echo "   Please install Python from https://www.python.org/downloads/"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi
echo "   ✅ Found: $($PYTHON --version)"
echo ""

# ── Step 2: Install dependencies (only if missing) ────────────
echo "📦 Checking dependencies..."
MISSING=0

check_pkg() {
    $PYTHON -c "import $1" 2>/dev/null || MISSING=1
}

check_pkg flask
check_pkg matplotlib
check_pkg numpy
check_pkg pandas
check_pkg yfinance

if [ $MISSING -eq 1 ]; then
    echo "   ⬇️  Installing missing packages (one-time setup)..."
    echo ""
    $PYTHON -m pip install --quiet flask matplotlib numpy pandas yfinance --break-system-packages 2>/dev/null || \
    $PYTHON -m pip install --quiet flask matplotlib numpy pandas yfinance
    echo "   ✅ Packages installed!"
else
    echo "   ✅ All packages ready!"
fi
echo ""

# ── Step 3: Kill any old instance on port 8080 ───────────────
OLD_PID=$(lsof -ti:8080 2>/dev/null)
if [ ! -z "$OLD_PID" ]; then
    echo "♻️  Stopping previous server (PID $OLD_PID)..."
    kill $OLD_PID 2>/dev/null
    sleep 1
fi

# ── Step 4: Start the server ─────────────────────────────────
echo "🚀 Starting Options Dashboard server..."
echo ""
cd "$SCRIPTS_DIR"

# Check for Alpaca API keys — if present use live mode, else demo
if [ ! -z "$ALPACA_API_KEY" ]; then
    echo "   🔑 Alpaca API key found — starting in PAPER mode"
    echo "      (Set ALPACA_PAPER=false in your env to use LIVE funds)"
    echo ""
    $PYTHON server.py &
else
    echo "   🎮 No API keys found — starting in DEMO mode"
    echo "      (To use real data, add your Alpaca API keys — see SETUP.md)"
    echo ""
    $PYTHON server.py --demo &
fi

SERVER_PID=$!
echo "   Server PID: $SERVER_PID"
echo ""

# ── Step 5: Wait for server to be ready ───────────────────────
echo "⏳ Waiting for server to start..."
MAX_WAIT=20
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8080 >/dev/null 2>&1; then
        break
    fi
    sleep 1
    WAITED=$((WAITED + 1))
    echo -n "."
done
echo ""
echo ""

# ── Step 6: Open browser ──────────────────────────────────────
if curl -s http://localhost:8080 >/dev/null 2>&1; then
    echo "✅ Server is running!"
    echo ""
    echo "🌐 Opening dashboard in your browser..."
    open http://localhost:8080
    echo ""
    echo "============================================================"
    echo "   Dashboard is live at: http://localhost:8080"
    echo ""
    echo "   💡 Keep this window open while using the dashboard."
    echo "      Close this window (or press Ctrl+C) to stop the server."
    echo "============================================================"
    echo ""
else
    echo "⚠️  Server took longer than expected to start."
    echo "   Try opening http://localhost:8080 manually in your browser."
    echo ""
fi

# Keep terminal open and follow server logs
wait $SERVER_PID
