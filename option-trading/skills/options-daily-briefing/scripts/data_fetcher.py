"""
Live Data Fetcher  (run on YOUR machine, not inside Claude)
============================================================
Fetches real OHLCV history and options chain data using yfinance
and saves a JSON file that the daily briefing tool can read.

Requirements (install on your own machine):
  pip install yfinance pandas numpy

Usage:
  python data_fetcher.py                               # default tickers
  python data_fetcher.py --tickers SPY QQQ AAPL NVDA  # custom list
  python data_fetcher.py --output ~/Desktop/market_data.json

Then open the generated JSON in the daily briefing:
  python daily_briefing.py --input ~/Desktop/market_data.json
"""

import json, sys, math, argparse
from datetime import date, datetime, timedelta

# ── Dependency check ─────────────────────────────────────────────────────────
try:
    import yfinance as yf
    import numpy as np
    import pandas as pd
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}")
    print("Install with:  pip install yfinance pandas numpy")
    sys.exit(1)

DEFAULT_TICKERS = ['SPY', 'QQQ', 'AAPL', 'NVDA', 'TSLA']
HISTORY_DAYS    = 252    # 1 year of daily bars

# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_float(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return 0.0
    return float(v)

def _fetch_ohlcv(ticker_sym: str):
    """Fetch 252 trading days of OHLCV from yfinance."""
    print(f"  [{ticker_sym}] Fetching price history...", flush=True)
    t = yf.Ticker(ticker_sym)
    df = t.history(period='1y', interval='1d', auto_adjust=True)
    df = df.dropna()
    dates   = [d.strftime('%Y-%m-%d') for d in df.index]
    opens   = [round(float(v), 4) for v in df['Open']]
    highs   = [round(float(v), 4) for v in df['High']]
    lows    = [round(float(v), 4) for v in df['Low']]
    closes  = [round(float(v), 4) for v in df['Close']]
    volumes = [int(v) for v in df['Volume']]
    price   = closes[-1] if closes else 0.0
    return dates, opens, highs, lows, closes, volumes, price

def _historical_vol(closes, window=30):
    """Compute 30-day realized volatility (annualised)."""
    if len(closes) < window + 1:
        return 0.20
    log_returns = [math.log(closes[i]/closes[i-1]) for i in range(1, len(closes))]
    recent = log_returns[-window:]
    mean = sum(recent)/len(recent)
    variance = sum((r - mean)**2 for r in recent) / (len(recent)-1)
    return round(math.sqrt(variance * 252), 4)

def _iv_rank(closes, iv_30d):
    """Approximate IV rank by comparing IV to the range of 30-day RV samples."""
    if len(closes) < 60:
        return 50.0
    rvs = []
    for i in range(30, len(closes)):
        window = closes[i-30:i]
        lr = [math.log(window[j]/window[j-1]) for j in range(1, len(window))]
        m = sum(lr)/len(lr)
        v = sum((r-m)**2 for r in lr)/(len(lr)-1)
        rvs.append(math.sqrt(v*252))
    if not rvs:
        return 50.0
    mn, mx = min(rvs), max(rvs)
    if mx == mn:
        return 50.0
    rank = (iv_30d - mn) / (mx - mn) * 100
    return round(min(100, max(0, rank)), 1)

def _fetch_options(ticker_sym: str, price: float):
    """
    Fetch options chain for the next 4 expiries.
    Returns { 'calls': {expiry: [...]}, 'puts': {expiry: [...]} }
    """
    print(f"  [{ticker_sym}] Fetching options chain...", flush=True)
    t = yf.Ticker(ticker_sym)
    try:
        expiries = t.options
    except Exception as e:
        print(f"  [{ticker_sym}] Options not available: {e}")
        return {'calls': {}, 'puts': {}}

    if not expiries:
        return {'calls': {}, 'puts': {}}

    today = date.today()
    future_expiries = [e for e in expiries if date.fromisoformat(e) > today][:4]

    calls_all, puts_all = {}, {}
    for exp_str in future_expiries:
        try:
            chain = t.option_chain(exp_str)
            dte = (date.fromisoformat(exp_str) - today).days

            def parse_side(df, opt_type):
                rows = []
                for _, row in df.iterrows():
                    K = _safe_float(row.get('strike'))
                    # Filter to strikes within ±15% of spot
                    if K < price * 0.85 or K > price * 1.15:
                        continue
                    rows.append({
                        'strike':        K,
                        'expiry':        exp_str,
                        'type':          opt_type,
                        'dte':           dte,
                        'iv':            round(_safe_float(row.get('impliedVolatility')), 4),
                        'bid':           round(_safe_float(row.get('bid')), 2),
                        'ask':           round(_safe_float(row.get('ask')), 2),
                        'mid':           round((_safe_float(row.get('bid')) + _safe_float(row.get('ask')))/2, 2),
                        'delta':         round(_safe_float(row.get('delta', 0)), 4),
                        'gamma':         round(_safe_float(row.get('gamma', 0)), 6),
                        'theta':         round(_safe_float(row.get('theta', 0)), 4),
                        'vega':          round(_safe_float(row.get('vega', 0)),  4),
                        'open_interest': int(_safe_float(row.get('openInterest', 0))),
                        'volume':        int(_safe_float(row.get('volume', 0))),
                        'last':          round(_safe_float(row.get('lastPrice', 0)), 2),
                    })
                return rows

            calls_all[exp_str] = parse_side(chain.calls, 'call')
            puts_all[exp_str]  = parse_side(chain.puts, 'put')
        except Exception as e:
            print(f"  [{ticker_sym}] Error fetching chain for {exp_str}: {e}")
            continue

    return {'calls': calls_all, 'puts': puts_all}

def _fetch_vix():
    """Fetch current VIX level."""
    try:
        t = yf.Ticker('^VIX')
        df = t.history(period='5d')
        if not df.empty:
            return round(float(df['Close'].iloc[-1]), 2)
    except Exception:
        pass
    return 17.5   # fallback

def fetch_all(tickers):
    """Fetch all data and return the input JSON dict."""
    today = date.today()
    while today.weekday() >= 5:
        today -= timedelta(days=1)

    print("Fetching VIX...", flush=True)
    vix = _fetch_vix()
    print(f"  VIX: {vix}", flush=True)

    result = {
        'date':    today.strftime('%Y-%m-%d'),
        'vix':     vix,
        'tickers': {}
    }

    for sym in tickers:
        print(f"\n[{sym}]", flush=True)
        try:
            dates, opens, highs, lows, closes, volumes, price = _fetch_ohlcv(sym)
            if not closes:
                print(f"  [{sym}] No price data, skipping.")
                continue

            rv30    = _historical_vol(closes, 30)
            iv_30d  = rv30 * 1.10   # crude IV estimate if options chain is unavailable

            opt_data = _fetch_options(sym, price)

            # Try to get a real ATM IV from options chain
            if opt_data['calls']:
                first_exp = list(opt_data['calls'].keys())[0]
                chain_calls = opt_data['calls'][first_exp]
                atm_candidates = [c for c in chain_calls if abs(c['strike'] - price) < price * 0.03]
                if atm_candidates:
                    iv_30d = round(sum(c['iv'] for c in atm_candidates) / len(atm_candidates), 4)

            ivr = _iv_rank(closes, iv_30d)

            # Beta vs SPY (simple: for now use DEFAULT_BETAS, user can override)
            BETAS = {'SPY':1.0,'QQQ':1.1,'IWM':1.05,'GLD':0.05,'TLT':-0.25,
                     'AAPL':1.20,'MSFT':1.05,'NVDA':1.70,'TSLA':1.85,'AMZN':1.15,
                     'GOOGL':1.10,'META':1.25,'AMD':1.60,'NFLX':1.30,'UBER':1.40}
            beta = BETAS.get(sym.upper(), 1.0)

            result['tickers'][sym] = {
                'ticker':  sym,
                'price':   round(price, 4),
                'beta':    beta,
                'dates':   dates,
                'opens':   opens,
                'highs':   highs,
                'lows':    lows,
                'closes':  closes,
                'volumes': volumes,
                'iv_30d':  iv_30d,
                'iv_rank': ivr,
                'calls':   opt_data['calls'],
                'puts':    opt_data['puts'],
            }
            print(f"  Done. Price=${price:.2f}  IV={iv_30d:.1%}  IVR={ivr:.0f}  "
                  f"Call expiries: {list(opt_data['calls'].keys())}")
        except Exception as e:
            print(f"  [{sym}] FAILED: {e}")
            import traceback; traceback.print_exc()
            continue

    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch live market data for daily briefing')
    parser.add_argument('--tickers', nargs='+', default=DEFAULT_TICKERS)
    parser.add_argument('--output',  default='market_data.json')
    args = parser.parse_args()

    print(f"Fetching data for: {args.tickers}")
    data = fetch_all(args.tickers)

    import os
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n✓ Data saved to: {args.output}")
    print(f"  Date: {data['date']}   VIX: {data['vix']}")
    for sym, td in data['tickers'].items():
        print(f"  {sym}: ${td['price']:.2f}  IV={td['iv_30d']:.1%}  IVR={td['iv_rank']:.0f}")
    print(f"\nNow run:\n  python daily_briefing.py --input {args.output}")
