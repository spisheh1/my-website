"""
Demo Data Generator
====================
Generates realistic synthetic OHLCV price history and options chain data
for testing the daily briefing tool without a live data feed.

Usage (standalone):
  python demo_data.py --output /path/to/data.json

Or import:
  from demo_data import generate_demo_input
  data = generate_demo_input()
"""
import json, math, random, argparse
from datetime import datetime, date, timedelta

# ── Reproducible seed so demo is stable each run ──────────────────────────────
random.seed(42)

# ── Realistic ticker profiles ─────────────────────────────────────────────────
TICKERS = {
    'SPY': {'price': 562.0,  'annual_vol': 0.14, 'beta': 1.00, 'div': 0.013},
    'QQQ': {'price': 480.0,  'annual_vol': 0.18, 'beta': 1.10, 'div': 0.006},
    'AAPL':{'price': 213.0,  'annual_vol': 0.22, 'beta': 1.20, 'div': 0.005},
    'NVDA':{'price': 875.0,  'annual_vol': 0.45, 'beta': 1.70, 'div': 0.001},
    'TSLA':{'price': 248.0,  'annual_vol': 0.55, 'beta': 1.85, 'div': 0.000},
}

VIX_BASE = 17.5   # baseline VIX

def _gbm_path(S0, mu, sigma, days, seed_offset=0):
    """Geometric Brownian Motion daily OHLCV simulation."""
    rng = random.Random(42 + seed_offset)
    dt = 1/252
    closes = [S0]
    for _ in range(days - 1):
        z = rng.gauss(0, 1)
        ret = math.exp((mu - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z)
        closes.append(closes[-1] * ret)

    opens, highs, lows, volumes = [], [], [], []
    avg_vol = S0 * 50_000_000 / S0   # ~50M shares equiv in $ terms
    for i, c in enumerate(closes):
        prev = closes[i-1] if i > 0 else c
        gap  = rng.gauss(0, sigma * math.sqrt(dt) * 0.5)
        o    = prev * math.exp(gap)
        intraday_range = abs(rng.gauss(0, sigma * math.sqrt(dt))) * c * 2
        h = max(o, c) + abs(rng.gauss(0, intraday_range * 0.3))
        l = min(o, c) - abs(rng.gauss(0, intraday_range * 0.3))
        vol = int(avg_vol * rng.uniform(0.6, 1.6))
        opens.append(round(o, 2))
        highs.append(round(h, 2))
        lows.append(round(l, 2))
        volumes.append(vol)

    return {
        'opens':   opens,
        'highs':   highs,
        'lows':    lows,
        'closes':  [round(c, 2) for c in closes],
        'volumes': volumes,
    }

def _trading_dates(end_date, n_days):
    """Generate n_days of trading dates ending at end_date (skip weekends)."""
    dates = []
    d = end_date
    while len(dates) < n_days:
        if d.weekday() < 5:   # Mon–Fri
            dates.append(d.strftime('%Y-%m-%d'))
        d -= timedelta(days=1)
    dates.reverse()
    return dates

def _iv_surface(S, sigma_atm, skew=-0.0015):
    """
    Simple parametric IV surface for demo options chain.
    sigma_atm: ATM implied vol
    skew: negative = put skew (typical for indices)
    Returns function: moneyness -> IV
    """
    def iv_for_strike(K):
        m = math.log(K / S)   # log-moneyness
        # skew + convexity (smile)
        return max(0.04, sigma_atm + skew * m * 100 + 0.005 * m**2 * 10000)
    return iv_for_strike

def _option_chain(S, iv_atm, expiry_date, today, opt_type='call'):
    """
    Build a mini options chain: 7 strikes around ATM for given expiry.
    Returns list of option dicts.
    """
    dte = max(1, (expiry_date - today).days)
    T   = dte / 365
    r   = 0.053   # ~5.3% risk-free rate

    iv_fn = _iv_surface(S, iv_atm)

    # ATM strike rounded to nearest 5 (for indices) or 2.5 (stocks)
    step = 5 if S > 200 else 2.5
    atm_k = round(S / step) * step
    strikes = [atm_k + step * i for i in range(-3, 4)]

    chain = []
    for K in strikes:
        iv = iv_fn(K)
        # Black-Scholes price
        try:
            d1 = (math.log(S/K) + (r + 0.5*iv**2)*T) / (iv*math.sqrt(T))
            d2 = d1 - iv * math.sqrt(T)
            def N(x):
                return 0.5 * (1 + math.erf(x / math.sqrt(2)))
            if opt_type == 'call':
                price = S * N(d1) - K * math.exp(-r*T) * N(d2)
                delta = N(d1)
            else:
                price = K * math.exp(-r*T) * N(-d2) - S * N(-d1)
                delta = N(d1) - 1
            gamma = math.exp(-d1**2/2) / (S * iv * math.sqrt(2*math.pi*T))
            theta = (-(S * math.exp(-d1**2/2) * iv) / (2*math.sqrt(2*math.pi*T))
                     - r * K * math.exp(-r*T) * (N(d2) if opt_type=='call' else N(-d2))) / 365
            vega  = S * math.exp(-d1**2/2) * math.sqrt(T) / math.sqrt(2*math.pi) / 100
        except (ValueError, ZeroDivisionError):
            continue

        oi   = int(random.uniform(500, 8000))
        volume = int(oi * random.uniform(0.02, 0.25))
        mid  = round(price, 2)
        bid  = round(max(0.01, mid * 0.97), 2)
        ask  = round(mid * 1.03, 2)

        chain.append({
            'strike':     K,
            'expiry':     expiry_date.strftime('%Y-%m-%d'),
            'type':       opt_type,
            'dte':        dte,
            'iv':         round(iv, 4),
            'bid':        bid,
            'ask':        ask,
            'mid':        mid,
            'delta':      round(delta, 4),
            'gamma':      round(gamma, 6),
            'theta':      round(theta, 4),
            'vega':       round(vega, 4),
            'open_interest': oi,
            'volume':     volume,
        })
    return chain

def _next_expiries(today, count=5):
    """Return the next 'count' standard 3rd-Friday expiries after today."""
    expiries = []
    year, month = today.year, today.month
    while len(expiries) < count:
        # 3rd Friday
        first_day = date(year, month, 1)
        first_fri = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
        third_fri = first_fri + timedelta(weeks=2)
        if third_fri > today:
            expiries.append(third_fri)
        month += 1
        if month > 12:
            month = 1
            year += 1
    return expiries

def generate_demo_input(today_str=None):
    """
    Generate full demo input dict ready to pass to daily_briefing.py
    Returns dict with keys: date, vix, tickers (dict of ticker -> data)
    """
    today = date.fromisoformat(today_str) if today_str else date.today()
    # Skip to next weekday if weekend
    while today.weekday() >= 5:
        today -= timedelta(days=1)

    expiries = _next_expiries(today, count=6)

    # VIX with slight randomness
    vix = round(VIX_BASE + random.gauss(0, 2), 1)

    result = {
        'date': today.strftime('%Y-%m-%d'),
        'vix':  vix,
        'tickers': {}
    }

    for i, (ticker, profile) in enumerate(TICKERS.items()):
        S0     = profile['price']
        sigma  = profile['annual_vol']
        mu     = 0.10   # 10% annualised drift

        # 252 days of history
        ohlcv  = _gbm_path(S0, mu, sigma, 252, seed_offset=i*100)
        dates  = _trading_dates(today, 252)
        S      = ohlcv['closes'][-1]   # current price

        # IV term structure: short-term slightly elevated, then contango
        iv_7d   = round(sigma * random.uniform(0.85, 1.15), 4)
        iv_30d  = round(sigma * random.uniform(0.90, 1.10), 4)
        iv_60d  = round(sigma * random.uniform(0.92, 1.08), 4)
        iv_90d  = round(sigma * random.uniform(0.95, 1.05), 4)

        # Build options chains for 4 expiry dates
        calls, puts = {}, {}
        for exp in expiries[:4]:
            dte  = (exp - today).days
            if dte <= 21:
                iv_e = iv_7d
            elif dte <= 45:
                iv_e = iv_30d
            elif dte <= 75:
                iv_e = iv_60d
            else:
                iv_e = iv_90d
            exp_str = exp.strftime('%Y-%m-%d')
            calls[exp_str] = _option_chain(S, iv_e, exp, today, 'call')
            puts[exp_str]  = _option_chain(S, iv_e, exp, today, 'put')

        # IV rank approximation (vs 252-day realized vol distribution)
        rv_samples = [sigma * random.uniform(0.5, 1.8) for _ in range(252)]
        rv_samples.sort()
        ivr = round(sum(1 for v in rv_samples if v < iv_30d) / len(rv_samples) * 100, 1)

        result['tickers'][ticker] = {
            'ticker':    ticker,
            'price':     round(S, 2),
            'beta':      profile['beta'],
            'dates':     dates,
            'opens':     ohlcv['opens'],
            'highs':     ohlcv['highs'],
            'lows':      ohlcv['lows'],
            'closes':    ohlcv['closes'],
            'volumes':   ohlcv['volumes'],
            'iv_30d':    iv_30d,
            'iv_rank':   ivr,
            'calls':     calls,
            'puts':      puts,
        }

    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate demo input data for daily briefing')
    parser.add_argument('--output', default='/sessions/peaceful-funny-dijkstra/mnt/outputs/options-daily-briefing/demo_input.json')
    parser.add_argument('--date',   default=None, help='YYYY-MM-DD override')
    args = parser.parse_args()

    data = generate_demo_input(args.date)
    import os; os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Demo data written to {args.output}")
    print(f"  Date : {data['date']}")
    print(f"  VIX  : {data['vix']}")
    print(f"  Tickers: {list(data['tickers'].keys())}")
    for t, td in data['tickers'].items():
        print(f"    {t}: ${td['price']:.2f}  IV30={td['iv_30d']:.1%}  IVR={td['iv_rank']:.0f}")
