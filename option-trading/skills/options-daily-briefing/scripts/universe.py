"""
Options Universe
=================
Defines the full tradeable options universe (all stocks with liquid options)
and generates realistic synthetic OHLCV + IV data for demo mode.

Live mode: data_fetcher.py pulls real data for all these tickers.
Demo mode: GBM simulation gives each ticker a realistic price history.
"""

import math, random
from datetime import date, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# Full options universe — every major ticker with liquid options
# Format: symbol -> (approx_price, annual_vol, sector, beta)
# ─────────────────────────────────────────────────────────────────────────────
OPTIONS_UNIVERSE = {
    # ── Mega-cap Tech ────────────────────────────────────────────────
    'AAPL':  (213,   0.22, 'Tech',    1.20),
    'MSFT':  (415,   0.20, 'Tech',    1.05),
    'NVDA':  (875,   0.45, 'Tech',    1.70),
    'GOOGL': (168,   0.24, 'Tech',    1.10),
    'META':  (505,   0.30, 'Tech',    1.25),
    'AMZN':  (195,   0.26, 'Tech',    1.15),
    'TSLA':  (248,   0.55, 'Tech',    1.85),
    'AMD':   (158,   0.48, 'Tech',    1.60),
    'INTC':  (22,    0.35, 'Tech',    0.90),
    'CRM':   (295,   0.28, 'Tech',    1.20),
    'ORCL':  (130,   0.24, 'Tech',    0.95),
    'ADBE':  (445,   0.30, 'Tech',    1.15),
    'NFLX':  (625,   0.32, 'Tech',    1.30),
    'AVGO':  (185,   0.28, 'Tech',    1.25),
    'QCOM':  (162,   0.30, 'Tech',    1.10),
    'TXN':   (188,   0.22, 'Tech',    0.95),
    'MU':    (98,    0.40, 'Tech',    1.45),
    'AMAT':  (188,   0.35, 'Tech',    1.30),
    'LRCX':  (780,   0.35, 'Tech',    1.35),
    'SNOW':  (155,   0.52, 'Tech',    1.55),
    'PLTR':  (28,    0.60, 'Tech',    1.65),
    'COIN':  (205,   0.65, 'Tech',    1.75),
    'UBER':  (78,    0.38, 'Tech',    1.40),
    'LYFT':  (12,    0.55, 'Tech',    1.50),
    'RBLX':  (38,    0.55, 'Tech',    1.45),
    'SHOP':  (98,    0.48, 'Tech',    1.50),

    # ── Financials ───────────────────────────────────────────────────
    'JPM':   (215,   0.20, 'Finance', 1.10),
    'BAC':   (38,    0.22, 'Finance', 1.15),
    'GS':    (520,   0.22, 'Finance', 1.20),
    'MS':    (105,   0.22, 'Finance', 1.15),
    'WFC':   (62,    0.20, 'Finance', 1.05),
    'C':     (65,    0.22, 'Finance', 1.10),
    'V':     (278,   0.16, 'Finance', 0.95),
    'MA':    (488,   0.16, 'Finance', 0.95),
    'AXP':   (265,   0.20, 'Finance', 1.10),
    'BLK':   (885,   0.20, 'Finance', 1.10),
    'SCHW':  (78,    0.25, 'Finance', 1.15),

    # ── Healthcare / Biotech ─────────────────────────────────────────
    'JNJ':   (155,   0.14, 'Health',  0.60),
    'LLY':   (800,   0.28, 'Health',  0.70),
    'UNH':   (525,   0.18, 'Health',  0.75),
    'PFE':   (27,    0.20, 'Health',  0.65),
    'MRK':   (105,   0.16, 'Health',  0.60),
    'ABBV':  (172,   0.18, 'Health',  0.75),
    'AMGN':  (298,   0.18, 'Health',  0.70),
    'GILD':  (88,    0.18, 'Health',  0.65),
    'BIIB':  (188,   0.30, 'Health',  0.80),
    'MRNA':  (72,    0.50, 'Health',  1.20),

    # ── Consumer / Retail ────────────────────────────────────────────
    'WMT':   (92,    0.14, 'Consumer',0.60),
    'COST':  (885,   0.16, 'Consumer',0.75),
    'TGT':   (148,   0.22, 'Consumer',0.85),
    'HD':    (368,   0.18, 'Consumer',0.90),
    'LOW':   (232,   0.18, 'Consumer',0.90),
    'MCD':   (288,   0.14, 'Consumer',0.65),
    'SBUX':  (92,    0.20, 'Consumer',0.85),
    'NKE':   (72,    0.22, 'Consumer',0.90),
    'DIS':   (98,    0.25, 'Consumer',1.00),

    # ── Energy ───────────────────────────────────────────────────────
    'XOM':   (112,   0.20, 'Energy',  0.85),
    'CVX':   (152,   0.18, 'Energy',  0.80),
    'COP':   (115,   0.25, 'Energy',  1.00),
    'SLB':   (42,    0.28, 'Energy',  1.05),
    'OXY':   (58,    0.28, 'Energy',  1.10),

    # ── Industrials ──────────────────────────────────────────────────
    'BA':    (172,   0.30, 'Indust',  1.10),
    'CAT':   (358,   0.22, 'Indust',  1.05),
    'GE':    (158,   0.25, 'Indust',  1.05),
    'MMM':   (118,   0.18, 'Indust',  0.90),
    'HON':   (215,   0.16, 'Indust',  0.85),
    'UPS':   (132,   0.18, 'Indust',  0.85),
    'FDX':   (275,   0.22, 'Indust',  1.05),

    # ── ETFs (most liquid options market) ───────────────────────────
    'SPY':   (562,   0.14, 'ETF',     1.00),
    'QQQ':   (480,   0.18, 'ETF',     1.10),
    'IWM':   (208,   0.20, 'ETF',     1.05),
    'GLD':   (238,   0.12, 'ETF',     0.05),
    'TLT':   (88,    0.14, 'ETF',    -0.25),
    'XLF':   (42,    0.16, 'ETF',     1.10),
    'XLE':   (92,    0.20, 'ETF',     0.85),
    'XLK':   (218,   0.20, 'ETF',     1.10),
    'XBI':   (95,    0.30, 'ETF',     1.00),
    'SMH':   (225,   0.30, 'ETF',     1.35),
    'ARKK':  (48,    0.50, 'ETF',     1.45),
    'VIX':   (17,    0.60, 'ETF',    -1.00),   # not buyable directly but useful
}

# Remove VIX from tradeable universe (it's not a stock)
TRADEABLE = {k: v for k, v in OPTIONS_UNIVERSE.items() if k != 'VIX'}


def _gbm_path(S0, sigma, days=252, mu=0.10, seed=0):
    """Fast GBM path generator."""
    rng = random.Random(seed)
    dt  = 1/252
    closes = [S0]
    for _ in range(days - 1):
        z = rng.gauss(0, 1)
        closes.append(closes[-1] * math.exp((mu - 0.5*sigma**2)*dt + sigma*math.sqrt(dt)*z))

    highs, lows, opens, vols = [], [], [], []
    for i, c in enumerate(closes):
        prev = closes[i-1] if i > 0 else c
        o = prev * math.exp(rng.gauss(0, sigma*math.sqrt(dt)*0.4))
        rng_range = abs(rng.gauss(0, sigma * math.sqrt(dt))) * c * 2
        h = max(o, c) + abs(rng.gauss(0, rng_range * 0.3))
        l = min(o, c) - abs(rng.gauss(0, rng_range * 0.3))
        opens.append(round(o, 2))
        highs.append(round(h, 2))
        lows.append(round(l, 2))
        vols.append(int(S0 * 500_000 * rng.uniform(0.5, 1.8)))

    return (
        [round(c, 2) for c in closes],
        highs, lows, opens, vols
    )


def _trading_dates(end_date, n=252):
    dates, d = [], end_date
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d.strftime('%Y-%m-%d'))
        d -= timedelta(days=1)
    return list(reversed(dates))


def generate_universe_demo(today_str=None, seed_base=42):
    """
    Generate a full universe of ticker data for demo mode.
    Returns dict: { ticker: {closes, highs, lows, opens, volumes, dates, price,
                              iv_30d, iv_rank, beta, sector} }
    """
    rng = random.Random(seed_base)
    today = date.fromisoformat(today_str) if today_str else date.today()
    while today.weekday() >= 5:
        today -= timedelta(days=1)

    dates = _trading_dates(today, 252)
    universe = {}
    for i, (sym, (price0, vol, sector, beta)) in enumerate(TRADEABLE.items()):
        closes, highs, lows, opens, volumes = _gbm_path(
            price0, vol, 252, seed=seed_base + i * 17)
        price = closes[-1]

        # IV = realized vol * random premium (1.0–1.3) simulating VRP
        rv = vol
        iv_30d = round(rv * rng.uniform(1.0, 1.3), 4)

        # IV rank vs simulated 252-day rv distribution
        rv_samples = sorted(rv * rng.uniform(0.5, 1.8) for _ in range(252))
        ivr = round(sum(1 for v in rv_samples if v < iv_30d) / 252 * 100, 1)

        universe[sym] = {
            'ticker':  sym,
            'price':   round(price, 2),
            'beta':    beta,
            'sector':  sector,
            'dates':   dates,
            'closes':  closes,
            'highs':   highs,
            'lows':    lows,
            'opens':   opens,
            'volumes': volumes,
            'iv_30d':  iv_30d,
            'iv_rank': ivr,
        }

    return universe
