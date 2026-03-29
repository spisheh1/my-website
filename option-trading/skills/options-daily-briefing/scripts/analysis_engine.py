"""
Options Analysis Engine
========================
Core math: Black-Scholes pricing, Greeks, probability calculations,
technical indicators, option scoring, trade recommendation generation.
"""

import math
import statistics
from datetime import datetime, timedelta
import numpy as np


# ─── Black-Scholes ────────────────────────────────────────────────────────────

def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def norm_pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

def bs_price(S, K, T, r, sigma, opt='call'):
    if T <= 1e-6:
        return max(S - K, 0) if opt == 'call' else max(K - S, 0)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if opt == 'call':
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

def bs_greeks(S, K, T, r, sigma, opt='call'):
    if T <= 1e-6:
        d = 1.0 if (opt == 'call' and S > K) else 0.0
        return {'delta': d, 'gamma': 0, 'theta': 0, 'vega': 0,
                'price': bs_price(S, K, T, r, sigma, opt)}
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    delta = norm_cdf(d1) if opt == 'call' else norm_cdf(d1) - 1
    gamma = norm_pdf(d1) / (S * sigma * math.sqrt(T))
    vega  = S * norm_pdf(d1) * math.sqrt(T) / 100
    th    = (-(S * norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
             - r * K * math.exp(-r * T) * (norm_cdf(d2) if opt == 'call' else norm_cdf(-d2)))
    price = bs_price(S, K, T, r, sigma, opt)
    return {'delta': delta, 'gamma': gamma, 'theta': th / 365,
            'vega': vega, 'price': price, 'd1': d1, 'd2': d2}

def bs_iv(price, S, K, T, r, opt='call', tol=1e-5, max_iter=100):
    """Solve for implied volatility via Newton-Raphson."""
    intrinsic = max(S - K, 0) if opt == 'call' else max(K - S, 0)
    if price <= intrinsic + 1e-6:
        return None
    sigma = 0.25
    for _ in range(max_iter):
        g = bs_greeks(S, K, T, r, sigma, opt)
        f = g['price'] - price
        if abs(g['vega']) < 1e-10:
            break
        sigma = sigma - f / (g['vega'] * 100)
        if sigma <= 0:
            sigma = 0.01
        if abs(f) < tol:
            break
    return sigma if 0.01 < sigma < 5.0 else None


# ─── Probability Calculations ─────────────────────────────────────────────────

def prob_expire_itm(S, K, T, r, sigma, opt='call'):
    """N(d2) — probability of option expiring in-the-money."""
    if T <= 1e-6:
        return 1.0 if ((opt == 'call' and S > K) or (opt == 'put' and S < K)) else 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return norm_cdf(d2) if opt == 'call' else norm_cdf(-d2)

def prob_touch_before_expiry(S, target, T, r, sigma, direction='up'):
    """
    Probability of stock TOUCHING the target price before expiry.
    Uses the reflection principle (barrier option approximation).
    For upward barrier: P = N(d2_barrier) + (S/H)^(2*mu/sigma^2) * N(d2_reflected)
    where mu = r - 0.5*sigma^2
    """
    if T <= 1e-6:
        return 1.0 if ((direction == 'up' and S >= target) or
                       (direction == 'down' and S <= target)) else 0.0
    H = target
    mu = r - 0.5 * sigma**2
    d1 = (math.log(S / H) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    exponent = 2 * mu / (sigma**2)
    try:
        reflection_term = (S / H) ** exponent
    except (OverflowError, ValueError):
        reflection_term = 0.0
    if direction == 'up':
        p = norm_cdf(d2) + reflection_term * norm_cdf(d1 - 2 * math.log(H / S) / (sigma * math.sqrt(T)))
    else:
        p = norm_cdf(-d2) + reflection_term * norm_cdf(-d1 + 2 * math.log(H / S) / (sigma * math.sqrt(T)))
    return min(max(p, 0.0), 1.0)

def expected_move(S, iv, dte):
    """1-sigma expected move of the underlying."""
    return S * iv * math.sqrt(dte / 365.0)

def option_profit_probability(S, K_buy, strike_target_underlying, T, r, sigma,
                               premium_paid, opt='call'):
    """
    Probability that this option trade is profitable at expiry.
    = P(underlying > K_buy + premium_paid/delta) for calls
    More precisely: P(option_value_at_expiry > premium_paid)
    = P(S_T > K_buy + premium_paid) for calls (assuming delta ≈ 1 at target)
    """
    breakeven = K_buy + premium_paid if opt == 'call' else K_buy - premium_paid
    return prob_expire_itm(S, breakeven, T, r, sigma, opt)


# ─── Technical Analysis ───────────────────────────────────────────────────────

def sma(prices, period):
    if len(prices) < period:
        return [None] * len(prices)
    result = [None] * (period - 1)
    for i in range(period - 1, len(prices)):
        result.append(sum(prices[i - period + 1:i + 1]) / period)
    return result

def ema(prices, period):
    result = [None] * (period - 1)
    if len(prices) < period:
        return [None] * len(prices)
    k = 2.0 / (period + 1)
    val = sum(prices[:period]) / period
    result.append(val)
    for p in prices[period:]:
        val = p * k + val * (1 - k)
        result.append(val)
    return result

def rsi(prices, period=14):
    if len(prices) < period + 1:
        return [None] * len(prices)
    result = [None] * period
    gains, losses = [], []
    for i in range(1, period + 1):
        d = prices[i] - prices[i - 1]
        gains.append(max(d, 0)); losses.append(max(-d, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for i in range(period, len(prices) - 1):
        d = prices[i + 1] - prices[i]
        avg_gain = (avg_gain * (period - 1) + max(d, 0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-d, 0)) / period
        rs = avg_gain / avg_loss if avg_loss > 1e-10 else 100
        result.append(100 - 100 / (1 + rs))
    result.append(None)
    return result

def macd(prices, fast=12, slow=26, signal=9):
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    macd_line = [f - s if f and s else None for f, s in zip(ema_fast, ema_slow)]
    valid = [x for x in macd_line if x is not None]
    if len(valid) < signal:
        return macd_line, [None] * len(macd_line), [None] * len(macd_line)
    sig = ema(valid, signal)
    sig_full = [None] * (len(macd_line) - len(valid)) + sig
    hist = [m - s if m and s else None for m, s in zip(macd_line, sig_full)]
    return macd_line, sig_full, hist

def bollinger_bands(prices, period=20, std_mult=2.0):
    s = sma(prices, period)
    result = []
    for i, mid in enumerate(s):
        if mid is None:
            result.append((None, None, None))
            continue
        window = prices[i - period + 1:i + 1]
        std = statistics.stdev(window) if len(window) > 1 else 0
        result.append((mid - std_mult * std, mid, mid + std_mult * std))
    return result

def find_support_resistance(highs, lows, closes, lookback=20):
    """Find key support and resistance levels from recent swing highs/lows."""
    n = len(closes)
    levels = []
    for i in range(2, min(lookback, n - 2)):
        idx = n - 1 - i
        # Swing high
        if highs[idx] > highs[idx - 1] and highs[idx] > highs[idx + 1] and \
           highs[idx] > highs[idx - 2] and highs[idx] > highs[idx + 2]:
            levels.append(('resistance', highs[idx]))
        # Swing low
        if lows[idx] < lows[idx - 1] and lows[idx] < lows[idx + 1] and \
           lows[idx] < lows[idx - 2] and lows[idx] < lows[idx + 2]:
            levels.append(('support', lows[idx]))
    return levels

def atr(highs, lows, closes, period=14):
    """Average True Range."""
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i-1]),
                 abs(lows[i] - closes[i-1]))
        trs.append(tr)
    if not trs:
        return 0
    result = [sum(trs[:period]) / period]
    for tr in trs[period:]:
        result.append((result[-1] * (period - 1) + tr) / period)
    return result[-1] if result else 0

def volume_trend(volumes, period=10):
    """Is recent volume above or below average?"""
    if len(volumes) < period:
        return 'neutral'
    recent_avg = sum(volumes[-5:]) / 5
    baseline = sum(volumes[-period:-5]) / (period - 5)
    if baseline == 0:
        return 'neutral'
    ratio = recent_avg / baseline
    if ratio > 1.3:
        return 'high'
    elif ratio < 0.7:
        return 'low'
    return 'normal'


# ─── Market Regime Detection ──────────────────────────────────────────────────

def detect_regime(closes, vix=None):
    """Detect current market regime: bull/bear/sideways, vol level."""
    if len(closes) < 50:
        return {'trend': 'unknown', 'strength': 'weak', 'vol_regime': 'normal'}

    s20 = sma(closes, 20)
    s50 = sma(closes, 50)
    rsi_vals = rsi(closes)

    c   = closes[-1]
    s20_now = next((v for v in reversed(s20) if v is not None), None)
    s50_now = next((v for v in reversed(s50) if v is not None), None)
    rsi_now = next((v for v in reversed(rsi_vals) if v is not None), None)

    if s20_now and s50_now:
        if c > s20_now > s50_now:
            trend = 'bullish'
            strength = 'strong' if c > s50_now * 1.05 else 'moderate'
        elif c < s20_now < s50_now:
            trend = 'bearish'
            strength = 'strong' if c < s50_now * 0.95 else 'moderate'
        else:
            trend = 'sideways'
            strength = 'weak'
    else:
        trend = 'sideways'; strength = 'weak'

    # Volatility regime from VIX or from price action
    if vix:
        if vix < 15:   vol_regime = 'low'
        elif vix < 22: vol_regime = 'normal'
        elif vix < 30: vol_regime = 'elevated'
        else:          vol_regime = 'high'
    else:
        # Use 20-day historical vol as proxy
        returns = [math.log(closes[i] / closes[i-1]) for i in range(1, len(closes))]
        recent_rv = statistics.stdev(returns[-20:]) * math.sqrt(252) * 100 if len(returns) >= 20 else 20
        if recent_rv < 15:   vol_regime = 'low'
        elif recent_rv < 25: vol_regime = 'normal'
        elif recent_rv < 35: vol_regime = 'elevated'
        else:                vol_regime = 'high'

    return {
        'trend': trend, 'strength': strength,
        'vol_regime': vol_regime, 'rsi': rsi_now,
        's20': s20_now, 's50': s50_now, 'price': c
    }


# ─── Option Selection Logic ───────────────────────────────────────────────────

def select_best_strike(S, iv, dte, timeframe, regime_trend, opt_type='call'):
    """
    Choose the optimal strike based on timeframe and market regime.
    Returns target delta and the corresponding strike.
    """
    T = dte / 365.0
    r = 0.05

    # Target delta based on timeframe and conviction
    if timeframe == 'short':   target_delta = 0.45   # near ATM — fast response
    elif timeframe == 'mid':   target_delta = 0.40   # slightly OTM for leverage
    else:                       target_delta = 0.65   # deep ITM for LEAPS/long-term

    # Adjust for regime
    if regime_trend == 'bullish' and timeframe == 'short':
        target_delta = 0.50   # ATM — full sensitivity
    if regime_trend == 'bearish' and opt_type == 'put':
        target_delta = 0.45

    # Find strike corresponding to target delta via BS
    best_strike = S  # start at ATM
    best_diff = 1e9
    for offset_pct in [x / 100.0 for x in range(-30, 31, 1)]:
        K = round(S * (1 + offset_pct) / 5) * 5  # round to nearest $5
        if K <= 0:
            continue
        g = bs_greeks(S, K, T, r, iv, opt_type)
        delta = abs(g['delta'])
        diff = abs(delta - target_delta)
        if diff < best_diff:
            best_diff = diff
            best_strike = K

    return best_strike

def score_trade(S, K, T, r, iv, opt_type, price_target, regime):
    """
    Score a trade 0–100 based on risk/reward, probability, and regime alignment.
    """
    g = bs_greeks(S, K, T, r, iv, opt_type)
    premium = g['price']
    if premium <= 0:
        return 0

    # P(profit at expiry)
    p_profit = prob_expire_itm(S, K, T, r, iv, opt_type)

    # P(touching target before expiry)
    direction = 'up' if opt_type == 'call' else 'down'
    p_touch = prob_touch_before_expiry(S, price_target, T, r, iv, direction)

    # Option value at target underlying price
    val_at_target = bs_price(price_target, K, max(T - 0.01, 0.001), r, iv, opt_type)
    rr = (val_at_target - premium) / premium if premium > 0 else 0

    # Regime alignment bonus
    regime_bonus = 0
    if regime['trend'] == 'bullish' and opt_type == 'call': regime_bonus = 10
    if regime['trend'] == 'bearish' and opt_type == 'put':  regime_bonus = 10
    if regime['vol_regime'] == 'low':  regime_bonus += 5   # cheap options, good for buyers

    # RSI confirmation
    rsi_val = regime.get('rsi', 50)
    rsi_bonus = 0
    if rsi_val and opt_type == 'call' and 40 < rsi_val < 70:  rsi_bonus = 8
    if rsi_val and opt_type == 'put'  and 30 < rsi_val < 60:  rsi_bonus = 8
    if rsi_val and opt_type == 'call' and rsi_val > 75:        rsi_bonus = -10  # overbought
    if rsi_val and opt_type == 'put'  and rsi_val < 25:        rsi_bonus = -10  # oversold

    score = (p_touch * 40) + (min(rr, 3) / 3 * 30) + regime_bonus + rsi_bonus
    return min(round(score), 100)


# ─── Price Target Calculation ─────────────────────────────────────────────────

def calculate_targets(S, iv, dte, closes, highs, lows, regime, opt_type='call'):
    """
    Calculate entry, target, and stop prices for the underlying.
    Uses support/resistance + expected move to find realistic targets.
    """
    em = expected_move(S, iv, dte)
    atr_val = atr(highs, lows, closes) if len(closes) > 14 else S * 0.01

    # Support/resistance levels
    sr_levels = find_support_resistance(highs, lows, closes)
    resistances = sorted([l[1] for l in sr_levels if l[0] == 'resistance' and l[1] > S])
    supports    = sorted([l[1] for l in sr_levels if l[0] == 'support'    and l[1] < S], reverse=True)

    if opt_type == 'call':
        # Target: nearest resistance, or 1-sigma move, whichever is more conservative
        one_sigma_target = S + em * 0.75
        if resistances and resistances[0] < S + em * 1.5:
            price_target = min(resistances[0], one_sigma_target)
        else:
            price_target = one_sigma_target
        price_stop = S - atr_val * 1.5
    else:
        one_sigma_target = S - em * 0.75
        if supports and supports[0] > S - em * 1.5:
            price_target = max(supports[0], one_sigma_target)
        else:
            price_target = one_sigma_target
        price_stop = S + atr_val * 1.5

    return {
        'price_target': round(price_target, 2),
        'price_stop':   round(price_stop, 2),
        'expected_move_1sig': round(em, 2),
        'atr': round(atr_val, 2),
        'resistances': [round(r, 2) for r in resistances[:3]],
        'supports':    [round(s, 2) for s in supports[:3]],
    }


# ─── Full Trade Recommendation Builder ───────────────────────────────────────

def build_recommendation(ticker, closes, opens, highs, lows, volumes, iv,
                          timeframe, vix=None, r=0.05, existing_options=None):
    """
    Build a complete trade recommendation for a given timeframe.

    timeframe: 'short' (7-21 DTE), 'mid' (30-60 DTE), 'long' (90-180 DTE)
    iv: implied volatility as decimal (0.25 = 25%)
    """
    S = closes[-1]
    regime = detect_regime(closes, vix)

    # DTE selection
    if timeframe == 'short':
        dte = 14
        dte_label = '7–21 DTE'
        expiry = (datetime.now() + timedelta(days=dte)).strftime('%b %d %Y')
    elif timeframe == 'mid':
        dte = 45
        dte_label = '30–60 DTE'
        expiry = (datetime.now() + timedelta(days=dte)).strftime('%b %d %Y')
    else:
        dte = 120
        dte_label = '90–180 DTE'
        expiry = (datetime.now() + timedelta(days=dte)).strftime('%b %d %Y')

    T = dte / 365.0

    # Direction based on regime + timeframe
    # Use the trend; neutral = call (markets drift up over time)
    opt_type = 'put' if regime['trend'] == 'bearish' and regime['strength'] == 'strong' else 'call'

    # Find best strike
    K = select_best_strike(S, iv, dte, timeframe, regime['trend'], opt_type)

    # Price targets for underlying
    targets = calculate_targets(S, iv, dte, closes, highs, lows, regime, opt_type)

    # Option pricing
    g = bs_greeks(S, K, T, r, iv, opt_type)
    premium = g['price']
    if premium <= 0:
        premium = max(bs_price(S, K, T, r, iv * 1.2, opt_type), 0.01)

    # Entry / target / stop for the OPTION
    option_at_target = bs_price(targets['price_target'], K, max(T - 0.01, 0.001), r, iv, opt_type)
    option_at_stop   = bs_price(targets['price_stop'],   K, max(T - 0.01, 0.001), r, iv * 1.1, opt_type)

    # Spread on option (estimated)
    spread_est = max(premium * 0.04, 0.02)
    entry_limit = round(premium + spread_est * 0.5, 2)   # buy at mid + small buffer
    entry_mid   = round(premium, 2)

    target_option_price = round(option_at_target, 2)
    stop_option_price   = round(max(option_at_stop, premium * 0.4), 2)

    # Profit/loss in $
    max_gain_per_contract = round((target_option_price - entry_mid) * 100, 0)
    max_loss_per_contract = round((entry_mid - stop_option_price)   * 100, 0)
    rr_ratio = round(max_gain_per_contract / max_loss_per_contract, 2) if max_loss_per_contract > 0 else 0

    # Probabilities
    p_itm     = prob_expire_itm(S, K, T, r, iv, opt_type)
    p_touch   = prob_touch_before_expiry(S, targets['price_target'], T, r, iv,
                                          'up' if opt_type == 'call' else 'down')
    p_profit  = option_profit_probability(S, K, targets['price_target'], T, r, iv, entry_mid, opt_type)

    score = score_trade(S, K, T, r, iv, opt_type, targets['price_target'], regime)

    # Build reasoning
    reasoning = build_reasoning(ticker, S, K, dte, iv, opt_type, regime,
                                  targets, p_touch, rr_ratio, g, vix)

    # IVR assessment
    if iv < 0.20:    iv_assessment = 'LOW (good time to buy options)'
    elif iv < 0.35:  iv_assessment = 'NORMAL'
    elif iv < 0.50:  iv_assessment = 'ELEVATED'
    else:             iv_assessment = 'HIGH (expensive — consider spreads)'

    return {
        'ticker':      ticker,
        'timeframe':   timeframe,
        'dte_label':   dte_label,
        'expiry':      expiry,
        'dte':         dte,

        # Underlying
        'current_price':  round(S, 2),
        'price_target':   targets['price_target'],
        'price_stop':     targets['price_stop'],
        'expected_move':  targets['expected_move_1sig'],

        # Option contract
        'opt_type':     opt_type.upper(),
        'strike':       K,
        'option_label': f"{ticker} {expiry} {K}{opt_type[0].upper()}",

        # Prices (option)
        'entry_price':  entry_mid,
        'entry_limit':  entry_limit,
        'target_price': target_option_price,
        'stop_price':   stop_option_price,

        # P&L
        'max_gain':  max_gain_per_contract,
        'max_loss':  max_loss_per_contract,
        'rr_ratio':  rr_ratio,

        # Greeks
        'delta':  round(g['delta'], 3),
        'gamma':  round(g['gamma'], 4),
        'theta':  round(g['theta'], 3),
        'vega':   round(g['vega'], 3),
        'iv':     round(iv * 100, 1),
        'iv_assessment': iv_assessment,

        # Probabilities
        'prob_itm':    round(p_itm   * 100, 1),
        'prob_touch':  round(p_touch * 100, 1),
        'prob_profit': round(p_profit * 100, 1),

        # Score & regime
        'score':   score,
        'regime':  regime,
        'reasoning': reasoning,
    }

def build_reasoning(ticker, S, K, dte, iv, opt_type, regime, targets, p_touch, rr, g, vix):
    """Generate natural language reasoning for the trade."""
    lines = []
    trend_emoji = '📈' if regime['trend'] == 'bullish' else '📉' if regime['trend'] == 'bearish' else '↔️'
    lines.append(f"{trend_emoji} <strong>Trend:</strong> {ticker} is in a <strong>{regime['strength']} {regime['trend']}</strong> regime.")

    if regime.get('s20') and regime.get('s50'):
        s20, s50 = regime['s20'], regime['s50']
        if S > s20 > s50:
            lines.append(f"📊 <strong>Moving Averages:</strong> Price ({S:.2f}) is above both the 20-SMA ({s20:.2f}) and 50-SMA ({s50:.2f}) — confirming the uptrend.")
        elif S < s20 < s50:
            lines.append(f"📊 <strong>Moving Averages:</strong> Price ({S:.2f}) is below both the 20-SMA ({s20:.2f}) and 50-SMA ({s50:.2f}) — confirming the downtrend.")
        else:
            lines.append(f"📊 <strong>Moving Averages:</strong> Price ({S:.2f}) is between 20-SMA ({s20:.2f}) and 50-SMA ({s50:.2f}) — mixed signals, be cautious.")

    rsi_val = regime.get('rsi')
    if rsi_val:
        if rsi_val > 70:
            lines.append(f"⚠️ <strong>RSI {rsi_val:.0f}:</strong> Overbought territory — momentum may stall. Consider waiting for a pullback before entry.")
        elif rsi_val < 30:
            lines.append(f"⚠️ <strong>RSI {rsi_val:.0f}:</strong> Oversold — potential bounce ahead. Watch for confirmation candle.")
        elif 45 < rsi_val < 65:
            lines.append(f"✅ <strong>RSI {rsi_val:.0f}:</strong> Healthy momentum zone — no extreme readings, supports the trade direction.")
        else:
            lines.append(f"📊 <strong>RSI {rsi_val:.0f}:</strong> Neutral zone.")

    if iv < 0.22:
        lines.append(f"✅ <strong>IV {iv*100:.0f}%:</strong> Implied volatility is low — options are cheap relative to history. Good time to buy directional premium.")
    elif iv > 0.40:
        lines.append(f"⚠️ <strong>IV {iv*100:.0f}%:</strong> Implied volatility is elevated — you're paying up for options. Consider a spread to reduce cost.")
    else:
        lines.append(f"📊 <strong>IV {iv*100:.0f}%:</strong> Normal implied volatility — fair pricing environment.")

    if targets['resistances'] and opt_type == 'call':
        lines.append(f"🎯 <strong>Target {targets['price_target']:.2f}:</strong> First resistance is at {targets['resistances'][0]:.2f}. Target is set conservatively within the 1-sigma expected move (±{targets['expected_move_1sig']:.2f}).")
    elif targets['supports'] and opt_type == 'put':
        lines.append(f"🎯 <strong>Target {targets['price_target']:.2f}:</strong> First support is at {targets['supports'][0]:.2f}. Target is set conservatively within the 1-sigma expected move.")

    lines.append(f"🎲 <strong>Probability of touching target before expiry: {p_touch*100:.0f}%.</strong> Risk/reward ratio: {rr:.1f}:1 — {'favorable' if rr >= 1.5 else 'tight — consider wider target or different strike'}.")

    lines.append(f"⏱️ <strong>Strike selection:</strong> The {K} {opt_type} (delta {g['delta']:.2f}) gives {'strong directional sensitivity' if abs(g['delta']) > 0.45 else 'leveraged exposure'} with {dte} days for the move to develop.")

    if vix and vix > 25:
        lines.append(f"🚨 <strong>VIX Alert:</strong> Market fear gauge is elevated at {vix:.1f}. The whole market is nervous — size positions conservatively and use defined risk structures.")

    return lines
