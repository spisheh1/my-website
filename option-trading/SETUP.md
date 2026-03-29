# Options Daily Briefing — Setup Guide

## Quick Start (Demo — no setup needed)

```bash
cd options-daily-briefing/scripts
pip install flask matplotlib numpy pandas
python server.py --demo
# Then open: http://localhost:8080
```

---

## Full Live Setup (Real Market Data + Order Execution)

### Step 1 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Create a FREE Alpaca account
1. Go to **https://alpaca.markets** → Sign up free
2. In the dashboard, click **Paper Trading** → **API Keys** → Generate new key
3. Copy your **API Key** and **Secret Key**

### Step 3 — Configure credentials (two ways)

**Option A — Environment variables (recommended)**
```bash
export ALPACA_API_KEY="PKXXXXXXXXXXXXXXX"
export ALPACA_SECRET_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export ALPACA_PAPER=true        # keep this true until you're ready for real money!
```

**Option B — Config file**
```bash
cat > ~/.options_briefing/config.json << 'EOF'
{
  "api_key":    "PKXXXXXXXXXXXXXXX",
  "secret_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "mode":       "paper"
}
EOF
chmod 600 ~/.options_briefing/config.json
```

### Step 4 — Run the server
```bash
python server.py
# Opens at http://localhost:8080
# Re-scans the full market every 60 seconds
# Positions update every 10 seconds
```

---

## Switching to Live Trading

> ⚠ **WARNING**: Live trading uses REAL money. Always test with paper trading first.

When you're ready:
```bash
# Change ALPACA_PAPER to false:
export ALPACA_PAPER=false
# OR edit ~/.options_briefing/config.json: "mode": "live"
```

In live mode, the dashboard shows a **⚠ LIVE TRADING** warning banner on every invest modal. You must explicitly confirm each order.

---

## Your Portfolio Data

All trade history is stored permanently at:
```
~/.options_briefing/portfolio.db
```

This file is **completely separate** from the app — app updates will **never** touch it.

**Backup your portfolio:**
```bash
cp ~/.options_briefing/portfolio.db ~/Desktop/portfolio_backup_$(date +%Y%m%d).db
```

**Export to JSON:**
```
Click "Export JSON" in the Portfolio panel, or:
GET http://localhost:8080/api/export
```

**View summary from command line:**
```bash
python scripts/portfolio.py
```

---

## Data Update Frequency

| What | How often | Notes |
|------|-----------|-------|
| Full market scan (79 tickers) | Every 60 seconds | Change with `--scan-every 30` |
| Open position prices | Every 10 seconds | Requires Alpaca connection |
| Auto stop/target execution | Every 10 seconds | Triggered by price check |
| Page reload needed | Never | SSE pushes updates live |

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Live dashboard |
| `GET /api/scan` | Latest scan results (JSON) |
| `GET /api/portfolio` | Portfolio summary + positions |
| `GET /api/account` | Alpaca account info |
| `POST /api/order` | Place a new order |
| `POST /api/close/{id}` | Close a position |
| `GET /api/stream` | SSE live update stream |
| `GET /api/export` | Export portfolio to JSON |

---

## Frequently Asked Questions

**Q: Is my trade data safe if the app updates?**
A: Yes. Portfolio data is at `~/.options_briefing/portfolio.db` — completely outside the app folder. Updates never touch it.

**Q: What's the difference between paper and live?**
A: Paper trading places simulated orders with real market prices but no real money. It's identical to live except you can't lose money. Always start with paper.

**Q: Does this guarantee profitable trades?**
A: No. This is a screening and analysis tool, not a guarantee. Options trading carries significant risk. Never risk more than you can afford to lose.

**Q: How do I get truly real-time options data?**
A: Sign up for Alpaca's **Unlimited data plan** (~$9/mo). The free tier has 15-minute delayed options data. For paper trading, real-time data is included free.

**Q: Can I add my own tickers?**
A: Yes — edit `universe.py` and add your ticker to `OPTIONS_UNIVERSE` with approximate price, volatility, sector, and beta.
