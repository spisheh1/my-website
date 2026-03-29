---
name: options-daily-briefing
description: >
  Generates a full-page options trading dashboard for the current trading day.
  Produces a self-contained HTML file with 3 timeframes (short 7-21 DTE,
  mid 30-60 DTE, long 90-180 DTE), showing for each ticker: the recommended
  option to buy, exact entry price, target sell price, probability of hitting
  target, P&L diagram, probability distribution chart, full candlestick price
  chart with indicators (SMA, Bollinger Bands, RSI, MACD), Greeks summary,
  and a written reasoning section. Supports live data (yfinance) or demo mode.
  Use when the user asks to generate their morning options briefing, daily
  options analysis, or wants to know which options to buy today.
---

# Options Daily Briefing Skill

## What This Does

Every morning, run this skill to get a complete options trading dashboard for the day. It analyses 5 tickers (SPY, QQQ, AAPL, NVDA, TSLA by default) across 3 timeframes and tells you:

- **Which option to buy** — ticker, type (call/put), strike, expiry
- **Entry price** — exact contract price to pay
- **Target sell price** — where to take profit
- **Stop loss** — where to cut the trade
- **Probability** — chance of hitting target before expiry
- **Score** — 0-100 conviction score
- **Charts** — full price chart, P&L diagram, probability distribution
- **Greeks** — delta, gamma, theta, vega
- **Reasoning** — why this trade, what the technicals say

---

## Quick Start

### Demo Mode (no setup needed)

```bash
cd options-daily-briefing/scripts
python daily_briefing.py --demo
```

Opens `output/briefing_YYYYMMDD.html` — a fully self-contained HTML file. Open it in any browser.

### Live Mode (real market data)

**Step 1** — Install yfinance on YOUR machine (not needed in Claude):
```bash
pip install yfinance pandas numpy
```

**Step 2** — Fetch today's market data:
```bash
python data_fetcher.py --tickers SPY QQQ AAPL NVDA TSLA --output market_data.json
```

**Step 3** — Generate the briefing:
```bash
python daily_briefing.py --input market_data.json
```

---

## Command Reference

### `daily_briefing.py`

| Flag | Default | Description |
|------|---------|-------------|
| `--demo` | off | Use synthetic demo data (no data file required) |
| `--input FILE` | — | Path to JSON from data_fetcher.py |
| `--output FILE` | `output/briefing_YYYYMMDD.html` | Output HTML path |
| `--tickers A B C` | all in input | Analyse only these tickers |
| `--top N` | 5 | Max tickers to analyse |

### `data_fetcher.py` (run on your machine)

| Flag | Default | Description |
|------|---------|-------------|
| `--tickers A B C` | SPY QQQ AAPL NVDA TSLA | Tickers to fetch |
| `--output FILE` | `market_data.json` | Where to save the JSON |

---

## Dashboard Layout

```
┌─────────────────────────────────────────────────────┐
│  📈 OPTIONS DAILY BRIEFING  — Mar 21 2026  VIX 17.5  │
├─────────────────────────────────────────────────────┤
│  Market Overview: SPY / QQQ / VIX  (90-day chart)   │
├────────────┬────────────┬────────────────────────────┤
│ SHORT-TERM │  MID-TERM  │  LONG-TERM                 │
│ 7–21 DTE   │  30–60 DTE │  90–180 DTE                │
├────────────┴────────────┴────────────────────────────┤
│  Per ticker × per timeframe trade card:              │
│  ┌──────────────────────────────────────────────┐    │
│  │ SPY  CALL  Score: 78/100   SHORT-TERM        │    │
│  │ Entry: $4.20  Target: $7.50  Stop: $2.10     │    │
│  │ Strike: $565  Expiry: Apr 4  DTE: 14         │    │
│  │ [Price Chart + Indicators]                   │    │
│  │ [P&L Diagram]  [Probability Distribution]    │    │
│  │ Delta: +0.38   Theta: -0.12  Vega: +0.09     │    │
│  │ P(touch target): 42%   P(profit at exp): 35% │    │
│  │ Reasoning: Bullish regime, RSI 55 rising...  │    │
│  │ ✓ Execution checklist                        │    │
│  └──────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

---

## How It Works

### Analysis Engine (`analysis_engine.py`)

1. **Market Regime Detection** — classifies the market as bullish/bearish/sideways with low/normal/elevated/high volatility using SMA200, RSI, ATR
2. **Strike Selection** — picks optimal strike based on regime, IV, and DTE (ATM for low IV, OTM for high IV and short-term momentum)
3. **Target Calculation** — uses ATR multiples + support/resistance levels + expected move (IV-based)
4. **Probability Calculation** — Black-Scholes N(d2) for P(ITM at expiry), barrier-option reflection principle for P(touch target before expiry)
5. **Trade Scoring** — 0-100 score combining: R:R ratio, probability, regime alignment, IV rank signal, DTE positioning

### Chart Builder (`chart_builder.py`)

- **Price Chart** — full candlestick with SMA20/50/200, Bollinger Bands, Volume, RSI panel, MACD panel. Target and stop levels annotated.
- **P&L Diagram** — option P&L at expiry + P&L at halfway point. Entry cost, target, stop, breakeven all marked.
- **Probability Distribution** — log-normal stock price distribution at expiry. Zones coloured: green (profit), red (loss), with P(touch), P(profit), P(ITM) callouts.
- **Market Overview** — compact 90-day line charts for SPY, QQQ, VIX.

### Dashboard Renderer (`dashboard_renderer.py`)

Generates a fully self-contained dark-theme HTML file (~6 MB) with all charts embedded as base64 PNGs. No internet required to open. Works offline.

---

## Timeframe Strategy Guide

| Timeframe | DTE Range | Best For | Key Signal |
|-----------|-----------|----------|------------|
| Short | 7–21 DTE | Momentum trades, event plays | RSI breakout, MACD cross |
| Mid | 30–60 DTE | Trend following, high-conviction | Regime + IV rank 30–50 |
| Long | 90–180 DTE | Macro thesis, LEAPS-style | Low IV entry, strong trend |

---

## Scripts Reference

| File | Purpose |
|------|---------|
| `daily_briefing.py` | Main runner — orchestrates everything |
| `analysis_engine.py` | Black-Scholes math, indicators, trade logic |
| `chart_builder.py` | All chart generation (matplotlib) |
| `dashboard_renderer.py` | HTML dashboard builder |
| `demo_data.py` | Synthetic data generator for testing |
| `data_fetcher.py` | Live yfinance data fetcher (run on your machine) |

---

## Adding Custom Tickers

```bash
# Live data with your tickers:
python data_fetcher.py --tickers SPY AMZN MSFT GOOGL META --output market_data.json
python daily_briefing.py --input market_data.json

# Demo with subset:
python daily_briefing.py --demo --tickers SPY QQQ
```

---

## Interpreting the Score

| Score | Meaning | Action |
|-------|---------|--------|
| 75–100 | High conviction | Full size — enter the trade |
| 55–74 | Moderate conviction | Half size — watch and confirm |
| 40–54 | Borderline | Paper trade or skip |
| 0–39 | Weak | Skip this timeframe |

---

## Data Sources

The tool uses two data modes:

**Demo Mode** — Geometric Brownian Motion synthetic prices + parametric IV surface. Useful for learning the dashboard and testing without internet.

**Live Mode** — `yfinance` for real OHLCV (1-year daily bars) + real options chains with bid/ask/IV/greeks/OI. For professional-grade data with greeks already computed, upgrade to:
- **MarketData.app** — $12/mo, best bang for buck
- **Tradier** — free with a brokerage account
- **Polygon.io** — institutional-grade, higher cost
- **IBKR TWS API** — free if you have an account (best for algo trading)

---

## Automation (Daily Cron)

To auto-generate each morning at 9:00 AM:

```bash
# On Mac/Linux — add to crontab:
0 9 * * 1-5 cd /path/to/options-daily-briefing/scripts && python data_fetcher.py && python daily_briefing.py --input market_data.json

# Or use the Claude schedule skill to set this up in Cowork
```
