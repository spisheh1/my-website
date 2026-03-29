"""
Market-Wide Options Screener
==============================
Scans the entire options universe, scores every ticker for each timeframe,
and returns the top-ranked picks per timeframe.

Each candidate is scored on:
  - Market regime alignment (trend + momentum)
  - IV rank signal (premium seller vs buyer setup)
  - Risk/reward ratio
  - Probability of hitting target
  - Liquidity proxy (ATR / price)
  - Momentum (RSI, MACD cross)
  - Volatility environment (VIX-adjusted)

Returns ranked list of trade candidates ready for table rendering.
"""

import math
from analysis_engine import (
    detect_regime, rsi, macd, atr, sma, bollinger_bands,
    find_support_resistance, bs_price, bs_greeks, bs_iv,
    prob_expire_itm, prob_touch_before_expiry,
    select_best_strike, calculate_targets, expected_move
)

# ─────────────────────────────────────────────────────────────────────────────
TIMEFRAMES = {
    'short': {'label': 'Short-Term (7–21 DTE)', 'dte': 14,  'dte_min':  7, 'dte_max': 21,  'desc': '1–3 weeks'},
    'mid':   {'label': 'Mid-Term (30–60 DTE)',  'dte': 45,  'dte_min': 30, 'dte_max': 60,  'desc': '4–8 weeks'},
    'long':  {'label': 'Long-Term (90–180 DTE)','dte': 120, 'dte_min': 90, 'dte_max': 180, 'desc': '3–6 months'},
}

R_RISK_FREE = 0.053   # ~5.3% fed funds

# ─────────────────────────────────────────────────────────────────────────────

def _quick_indicators(closes, highs, lows):
    """
    Fast single-pass indicator calculation.

    Return types from analysis_engine:
      atr()             -> float
      rsi()             -> list[float|None]
      sma()             -> list[float|None]
      macd()            -> (macd_line, signal_line, histogram) — each a list
      bollinger_bands() -> list of (lower, mid, upper) tuples
    """
    rsi14    = rsi(closes, 14)
    atr14    = atr(highs, lows, closes, 14)   # single float
    s20      = sma(closes, 20)
    s50      = sma(closes, 50)
    s200     = sma(closes, 200)
    bb       = bollinger_bands(closes, 20, 2.0)  # list of (lower, mid, upper)
    mc_line, mc_sig, _ = macd(closes, 12, 26, 9)

    def _last_valid(lst, default=0):
        """Return last non-None element of a list."""
        if not lst:
            return default
        for v in reversed(lst):
            if v is not None:
                return v
        return default

    # bollinger_bands returns list of tuples (lower, mid, upper)
    bb_lower, bb_mid, bb_upper = closes[-1]*0.98, closes[-1], closes[-1]*1.02
    if bb:
        last_bb = bb[-1]
        if last_bb and all(v is not None for v in last_bb):
            bb_lower, bb_mid, bb_upper = last_bb

    return {
        'rsi':      _last_valid(rsi14, 50),
        'macd':     _last_valid(mc_line, 0),
        'signal':   _last_valid(mc_sig,  0),
        'atr':      atr14 if atr14 else 0,   # already a float
        'sma20':    _last_valid(s20,  closes[-1]),
        'sma50':    _last_valid(s50,  closes[-1]),
        'sma200':   _last_valid(s200, closes[-1]),
        'bb_upper': bb_upper,
        'bb_lower': bb_lower,
        'bb_mid':   bb_mid,
    }


def _score_candidate(S, K, T, iv, opt_type, regime, targets,
                     p_touch, rr, ind, ivr, vix, delta=0.35):
    """
    Score a trade candidate 0–100.
    Higher = stronger conviction to enter.

    Component breakdown (max pts):
      Trend alignment        : 25
      Momentum (RSI + MACD)  : 22  (with SMA-stack bonus)
      Probability of touch   : 20
      Risk / Reward          : 15
      IV rank (cheap options): 10
      Delta quality          :  5  (sweet-spot delta = best leverage/prob balance)
      VIX / macro            :  3
      ─────────────────────────────
      Max possible           : 100
    """
    score   = 0.0
    trend   = regime.get('trend', 'sideways')
    r14     = ind.get('rsi', 50)
    macd_v  = ind.get('macd', 0)
    macd_s  = ind.get('signal', 0)
    sma20   = ind.get('sma20', S)
    sma50   = ind.get('sma50', S)
    sma200  = ind.get('sma200', S)
    is_call = opt_type == 'call'

    # ── 1. Trend alignment (25 pts) ──────────────────────────────────
    if is_call:
        if trend == 'bullish':    score += 25
        elif trend == 'sideways': score += 10   # neutral context
        # bearish trend → 0 pts for call (momentum fighting us)
    else:
        if trend == 'bearish':    score += 25
        elif trend == 'sideways': score += 10
        # bullish trend → 0 pts for put

    # ── 2. Momentum (up to 22 pts) ───────────────────────────────────
    macd_bullish = macd_v > macd_s

    if is_call:
        # RSI sweet spot: 45–68 → healthy uptrend with room to run
        if 45 <= r14 <= 68:   score += 10
        elif r14 > 68:        score += 4    # overbought — momentum extended
        elif 35 <= r14 < 45:  score += 6   # recovering, not ideal
        else:                 score += 2   # oversold (< 35) could bounce but risky

        if macd_bullish:      score += 9   # confirmed bullish cross
        else:                 score += 0

        # SMA stacking bonus (3 pts): price > sma20 > sma50 = textbook uptrend
        if S > sma20 and sma20 > sma50:
            score += 3
    else:  # put
        # RSI sweet spot for puts: 32–55
        if 32 <= r14 <= 55:   score += 10
        elif r14 < 32:        score += 4   # oversold — bounce risk for put buyer
        elif 55 < r14 <= 65:  score += 6
        else:                 score += 2   # overbought (>65) — good for fade, but risky

        if not macd_bullish:  score += 9   # MACD below signal → bearish
        else:                 score += 0

        # SMA stacking bonus for puts: price < sma20 < sma50 = confirmed downtrend
        if S < sma20 and sma20 < sma50:
            score += 3

    # ── 3. Probability of touching target (20 pts) ───────────────────
    # p_touch is the highest-quality single signal — weight it most
    if   p_touch >= 0.60: score += 20
    elif p_touch >= 0.50: score += 16
    elif p_touch >= 0.40: score += 12
    elif p_touch >= 0.30: score += 7
    elif p_touch >= 0.22: score += 3

    # ── 4. Risk / Reward (15 pts) ────────────────────────────────────
    if   rr >= 3.0: score += 15
    elif rr >= 2.5: score += 13
    elif rr >= 2.0: score += 10
    elif rr >= 1.7: score += 7
    elif rr >= 1.4: score += 4

    # ── 5. IV rank — cheap options are better buys (10 pts) ──────────
    if   ivr < 20: score += 10   # very cheap IV — ideal for buying
    elif ivr < 35: score += 8
    elif ivr < 50: score += 6
    elif ivr < 65: score += 3
    else:          score += 1    # expensive IV — penalise premium buyers

    # ── 6. Delta quality — sweet-spot delta (5 pts) ──────────────────
    # 0.30–0.55 delta: good balance of leverage and probability of profit
    d = abs(delta)
    if   0.35 <= d <= 0.55: score += 5
    elif 0.30 <= d <  0.35: score += 4
    elif 0.25 <= d <  0.30: score += 2
    elif 0.55 <  d <= 0.70: score += 3   # ITM — works but pricier
    else:                   score += 0   # too far OTM or too deep ITM

    # ── 7. VIX / macro (3 pts) ──────────────────────────────────────
    # Calls: benefit from low VIX (calm market = upward drift)
    # Puts:  benefit from rising VIX (fear = falling stocks)
    if is_call:
        if   vix < 15: score += 3
        elif vix < 20: score += 2
        elif vix < 25: score += 1
    else:
        if   vix > 25: score += 3   # elevated fear = put-friendly
        elif vix > 20: score += 2
        elif vix > 15: score += 1

    return min(100, round(score, 1))


def _build_reasoning(ticker, S, K, dte, iv, ivr, opt_type, regime, ind,
                     vix, entry_price, opt_target, opt_stop, price_target,
                     stop_loss, breakeven, p_touch, p_profit, rr, score,
                     delta, theta, vega, gamma):
    """
    Build a structured reasoning object for the detail panel.
    Returns a dict with sections: setup, technicals, option_logic,
    probabilities, risk_management, execution, risks.
    """
    trend      = regime.get('trend', 'sideways')
    vol_regime = regime.get('vol_regime', 'normal')
    strength   = regime.get('strength', 'moderate')
    rsi14      = ind.get('rsi', 50)
    macd_v     = ind.get('macd', 0)
    macd_s     = ind.get('signal', 0)
    sma20      = ind.get('sma20', S)
    sma50      = ind.get('sma50', S)
    sma200     = ind.get('sma200', S)
    atr_val    = ind.get('atr', S * 0.01)
    bb_upper   = ind.get('bb_upper', S * 1.02)
    bb_lower   = ind.get('bb_lower', S * 0.98)
    is_call    = opt_type.lower() == 'call'

    em_1sig  = round(S * iv * math.sqrt(dte / 365), 2)
    moneyness = round((K - S) / S * 100, 1)
    moneyness_str = (f"ATM" if abs(moneyness) < 1 else
                     f"{'OTM' if is_call == (K > S) else 'ITM'} "
                     f"({abs(moneyness):.1f}% {'above' if K > S else 'below'})")

    # IV environment narrative
    if ivr < 25:
        iv_narrative = (f"IV rank is low at {ivr:.0f} — options are cheap relative to historical norms. "
                        f"This is a favorable environment for buying premium.")
    elif ivr < 50:
        iv_narrative = (f"IV rank is moderate at {ivr:.0f}. Options are fairly priced. "
                        f"Enter on a confirmed technical signal.")
    elif ivr < 75:
        iv_narrative = (f"IV rank is elevated at {ivr:.0f}. Options are somewhat expensive. "
                        f"Prefer tighter strikes or shorter expiry to limit IV risk.")
    else:
        iv_narrative = (f"IV rank is HIGH at {ivr:.0f} — options are expensive. "
                        f"Consider a spread instead of a naked long to reduce vega exposure.")

    # Trend narrative
    if trend == 'bullish':
        trend_narrative = (f"{ticker} is in a confirmed {strength} uptrend. "
                           f"Price is trading above SMA20 (${sma20:.2f}), SMA50 (${sma50:.2f}), "
                           f"and SMA200 (${sma200:.2f}), all in bullish alignment.")
    elif trend == 'bearish':
        trend_narrative = (f"{ticker} is in a confirmed {strength} downtrend. "
                           f"Price is below key moving averages: SMA20 (${sma20:.2f}), "
                           f"SMA50 (${sma50:.2f}), SMA200 (${sma200:.2f}). "
                           f"Bearish structure favors put options.")
    else:
        trend_narrative = (f"{ticker} is in a sideways/consolidating regime. "
                           f"Price is oscillating around SMA20 (${sma20:.2f}) and "
                           f"SMA50 (${sma50:.2f}). Looking for a breakout or mean-reversion setup.")

    # RSI narrative
    if rsi14 > 70:
        rsi_narrative = f"RSI is overbought at {rsi14:.0f}. Momentum is extended — risk of pullback."
    elif rsi14 < 30:
        rsi_narrative = f"RSI is oversold at {rsi14:.0f}. Momentum is deeply compressed — potential bounce."
    elif rsi14 > 55 and is_call:
        rsi_narrative = f"RSI at {rsi14:.0f} — showing bullish momentum, confirming the call setup."
    elif rsi14 < 45 and not is_call:
        rsi_narrative = f"RSI at {rsi14:.0f} — showing bearish momentum, confirming the put setup."
    else:
        rsi_narrative = f"RSI at {rsi14:.0f} — neutral territory, not giving a strong directional signal."

    # MACD narrative
    macd_cross = macd_v > macd_s
    if macd_cross and is_call:
        macd_narrative = (f"MACD ({macd_v:.3f}) crossed above signal ({macd_s:.3f}) — "
                          f"a bullish momentum cross confirming the call direction.")
    elif not macd_cross and not is_call:
        macd_narrative = (f"MACD ({macd_v:.3f}) is below signal ({macd_s:.3f}) — "
                          f"bearish momentum confirming the put direction.")
    elif macd_cross and not is_call:
        macd_narrative = (f"MACD ({macd_v:.3f}) is bullish but we're trading a put. "
                          f"Other signals (trend, RSI) overrode MACD. Watch for MACD to roll over.")
    else:
        macd_narrative = (f"MACD ({macd_v:.3f}) vs signal ({macd_s:.3f}) — "
                          f"momentum is mixed. Confirm entry with price action.")

    # Strike logic
    strike_logic = (f"The ${K:.2f} strike was selected as {moneyness_str}. "
                    f"Delta of {abs(delta):.2f} means this option moves approximately "
                    f"${abs(delta):.2f} for every $1.00 move in {ticker}. "
                    f"{'Higher delta strikes offer more leverage but cost more premium.' if abs(delta) > 0.45 else 'This OTM position offers high leverage at lower cost — needs a meaningful move to profit.'}")

    # Theta narrative
    theta_cost = abs(theta) * dte
    theta_narrative = (f"Theta is {theta:.3f}/day — this position loses approximately "
                       f"${abs(theta):.3f} per day to time decay. Over {dte} days that's "
                       f"~${theta_cost:.2f} total if the stock doesn't move. "
                       f"{'Time decay is a significant headwind — the stock needs to move soon.' if abs(theta) > entry_price * 0.015 else 'Time decay is manageable given the expected move.'}")

    # Vega narrative
    vega_narrative = (f"Vega is {vega:.3f} — each 1% change in IV affects the option value by "
                      f"~${vega:.3f}. {'With elevated IV, a crush in volatility could hurt this position even if the stock moves the right way.' if ivr > 60 else 'IV is low enough that vega risk is limited.'}")

    # Expected move vs target
    target_vs_em = round((price_target - S) / em_1sig * 100, 0) if em_1sig else 100
    if is_call:
        move_needed = round((price_target - S) / S * 100, 1)
    else:
        move_needed = round((S - price_target) / S * 100, 1)
    em_narrative = (f"The options market implies a 1-sigma move of ±${em_1sig:.2f} ({round(em_1sig/S*100,1)}%) "
                    f"over {dte} days. The target requires a {move_needed:.1f}% move, "
                    f"which is {abs(target_vs_em):.0f}% of the expected move. "
                    f"{'This is an achievable target within the expected range.' if abs(target_vs_em) <= 110 else 'This target is beyond the expected move — treat it as a stretch goal.'}")

    # Bollinger band context
    bb_position = round((S - bb_lower) / (bb_upper - bb_lower) * 100, 0) if bb_upper > bb_lower else 50
    if bb_position > 80:
        bb_narrative = f"Price is near the upper Bollinger Band ({bb_position:.0f}th percentile) — momentum is strong but extended."
    elif bb_position < 20:
        bb_narrative = f"Price is near the lower Bollinger Band ({bb_position:.0f}th percentile) — potential support / mean reversion zone."
    else:
        bb_narrative = f"Price is within the Bollinger Band middle range ({bb_position:.0f}th percentile) — no extreme compression or expansion."

    # Entry timing
    if dte <= 21:
        timing_note = ("Short-term option — enter early in the week if possible. "
                       "These options decay quickly; have a clear plan for same-week exit if the move comes early.")
    elif dte <= 60:
        timing_note = ("Mid-term window — you have time for the thesis to develop. "
                       "Consider scaling in: enter half position now, add on a confirming candle.")
    else:
        timing_note = ("Long-dated position — time is on your side. "
                       "You can weather short-term noise. Review every 2–3 weeks and adjust if trend changes.")

    # Risk factors
    risks = []
    if ivr > 60:
        risks.append(f"HIGH IV RISK: IVR={ivr:.0f} — if volatility collapses after entry, option value drops even if stock moves correctly.")
    if abs(delta) < 0.25:
        risks.append(f"LOW PROBABILITY: Delta {abs(delta):.2f} means this is a low-probability bet — size accordingly (max 1–2% of portfolio).")
    if rsi14 > 68 and is_call:
        risks.append(f"OVERBOUGHT: RSI={rsi14:.0f} — short-term pullback risk. Entering overbought names requires a tighter stop.")
    if rsi14 < 32 and not is_call:
        risks.append(f"OVERSOLD: RSI={rsi14:.0f} — could bounce. A dead-cat bounce could stop you out on the put before the real move.")
    if dte <= 14:
        risks.append(f"TIME RISK: Only {dte} DTE — theta decay is aggressive. If stock doesn't move in 3–5 days, consider exiting.")
    if not risks:
        risks.append("No major structural red flags — this is a clean setup with reasonable risk profile.")

    # Position sizing suggestion
    max_loss_pct = 1.5 if score >= 75 else (1.0 if score >= 55 else 0.5)
    sizing_note = (f"Suggested max loss = {max_loss_pct:.1f}% of portfolio. "
                   f"If your account is $50K, risk no more than ${50000 * max_loss_pct / 100:.0f} on this trade. "
                   f"At a stop of ${opt_stop:.2f}, that means buying "
                   f"{max(1, int(50000 * max_loss_pct / 100 / max(0.01, (entry_price - opt_stop) * 100)))}"
                   f" contract(s) for a $50K account.")

    return {
        'setup': {
            'headline': (f"{'Bullish' if is_call else 'Bearish'} {opt_type.upper()} on {ticker} — "
                         f"Score {score:.0f}/100, {dte} DTE, {moneyness_str}"),
            'trend':     trend_narrative,
            'iv':        iv_narrative,
            'em':        em_narrative,
        },
        'technicals': {
            'rsi':   rsi_narrative,
            'macd':  macd_narrative,
            'bb':    bb_narrative,
            'sma':   (f"Moving averages — SMA20: ${sma20:.2f} | SMA50: ${sma50:.2f} | "
                      f"SMA200: ${sma200:.2f}. "
                      f"Price (${S:.2f}) is {'above' if S > sma20 else 'below'} SMA20, "
                      f"{'above' if S > sma50 else 'below'} SMA50, "
                      f"{'above' if S > sma200 else 'below'} SMA200."),
            'atr':   (f"ATR(14) = ${atr_val:.2f} ({round(atr_val/S*100,1)}% daily range). "
                      f"This is the average true range — your stop is "
                      f"{round(abs(S - stop_loss)/atr_val, 1)}× ATR away from current price."),
        },
        'option_logic': {
            'strike':  strike_logic,
            'theta':   theta_narrative,
            'vega':    vega_narrative,
            'timing':  timing_note,
        },
        'probabilities': {
            'p_touch':  (f"{p_touch*100:.1f}% probability of touching the target price "
                         f"(${price_target:.2f}) at any point before expiry. "
                         f"This uses the barrier option reflection principle — "
                         f"it's higher than the probability of being there at expiry."),
            'p_profit': (f"{p_profit*100:.1f}% probability this option expires in-the-money "
                         f"(stock above ${K:.2f} at expiry). Calculated from Black-Scholes N(d2)."),
            'breakeven':(f"Stock must reach ${breakeven:.2f} at expiry for this trade to break even. "
                         f"That's a {round(abs(breakeven-S)/S*100,1)}% move from current price."),
            'rr':       (f"Risk/Reward = {rr:.1f}x. You risk ${round(entry_price - opt_stop,2):.2f} "
                         f"per option to make ${round(opt_target - entry_price,2):.2f}. "
                         f"{'Excellent R:R — this is worth the capital allocation.' if rr >= 2.5 else 'Acceptable R:R — standard for directional options.' if rr >= 1.5 else 'Thin R:R — only enter if you have very high conviction on the move.'}"),
        },
        'risk_management': {
            'sizing':   sizing_note,
            'stop':     (f"Stop the OPTION at ${opt_stop:.2f} (a {round((entry_price-opt_stop)/entry_price*100,0):.0f}% loss). "
                         f"This corresponds to the stock hitting ${stop_loss:.2f}. "
                         f"If breached, exit immediately — do not average down on losing options."),
            'target':   (f"Take 50–75% profit when the option hits ${round(opt_target*0.7,2):.2f}. "
                         f"Let runners go to full target ${opt_target:.2f}. "
                         f"Never let a +50% winner turn into a loser."),
            'risks':    risks,
        },
        'execution': [
            f"Check bid/ask spread before entering — max acceptable spread is 15% of mid price.",
            f"Enter as a limit order at mid (${entry_price:.2f}) or 1 tick better.",
            f"Set a stop-loss alert at ${opt_stop:.2f} immediately after fill.",
            f"Set a profit alert at ${round(opt_target * 0.65, 2):.2f} (65% of target) to start trailing.",
            f"Review position daily at market open — reassess if stock gaps the wrong way.",
            timing_note,
        ],
    }


def scan_ticker(ticker_data: dict, timeframe: str, vix: float = 18.0):
    """
    Score a single ticker for a given timeframe.
    Returns a candidate dict or None if unsuitable.
    """
    closes  = ticker_data.get('closes', [])
    highs   = ticker_data.get('highs', [])
    lows    = ticker_data.get('lows', [])
    iv      = ticker_data.get('iv_30d', 0.20)
    ivr     = ticker_data.get('iv_rank', 50.0)
    ticker  = ticker_data.get('ticker', '?')

    if len(closes) < 30:
        return None

    S   = closes[-1]
    tf  = TIMEFRAMES[timeframe]
    dte = tf['dte']
    T   = dte / 365

    # Indicators
    try:
        ind = _quick_indicators(closes, highs, lows)
    except Exception:
        return None

    # Regime
    try:
        regime = detect_regime(closes, vix)
    except Exception:
        regime = {'trend': 'sideways', 'vol_regime': 'normal', 'strength': 0.5}

    # ── Decide option type based on trend + momentum ────────────────────────
    trend     = regime.get('trend', 'sideways')
    r14       = ind.get('rsi', 50)
    macd_val  = ind.get('macd', 0)
    macd_sig  = ind.get('signal', 0)
    macd_bull = macd_val > macd_sig

    if trend == 'bullish':
        opt_type = 'call'
    elif trend == 'bearish':
        opt_type = 'put'
    else:
        # Sideways: use RSI + MACD cross to determine direction
        # Score: +1 for each bullish signal
        bull_signals = int(macd_bull) + int(r14 >= 50)
        if bull_signals >= 2:
            opt_type = 'call'   # both momentum signals bullish
        elif bull_signals == 0:
            opt_type = 'put'    # both bearish
        else:
            # Mixed — use RSI as tiebreaker
            opt_type = 'call' if r14 >= 50 else 'put'

    # ── Hard filters: avoid entering when momentum strongly contradicts ──────
    # Don't buy calls into overbought + bearish MACD divergence
    if opt_type == 'call' and r14 > 72 and not macd_bull:
        return None   # overbought AND losing momentum — risky call entry
    # Don't buy puts into oversold + bullish MACD (bounce risk)
    if opt_type == 'put' and r14 < 28 and macd_bull:
        return None   # oversold AND momentum turning up — risky put entry

    # Strike selection
    try:
        K = select_best_strike(S, iv, dte, timeframe, trend, opt_type)
    except Exception:
        K = S * (1.02 if opt_type == 'call' else 0.98)
        K = round(K / 5) * 5 if S > 50 else round(K / 0.5) * 0.5

    # ── Option price: prefer real chain data over Black-Scholes ──────────────
    from datetime import date as _date
    chain_key    = 'calls' if opt_type == 'call' else 'puts'
    chain_data   = ticker_data.get(chain_key, {})
    real_option  = None
    chain_expiry = None   # will be used later for expiry string

    if chain_data:
        today_d = _date.today()
        best_diff, best_chain_exp = float('inf'), None
        for exp_str_c, opts in chain_data.items():
            try:
                diff = abs((_date.fromisoformat(exp_str_c) - today_d).days - dte)
                if diff < best_diff:
                    best_diff, best_chain_exp = diff, exp_str_c
            except Exception:
                continue
        if best_chain_exp:
            opts_for_exp = chain_data[best_chain_exp]
            if opts_for_exp:
                best_opt = min(opts_for_exp, key=lambda o: abs(o['strike'] - K))
                if abs(best_opt['strike'] - K) <= K * 0.08:  # within 8% of target strike
                    real_option  = best_opt
                    chain_expiry = best_chain_exp

    if real_option and real_option.get('mid', 0) >= 0.05:
        K           = real_option['strike']
        entry_price = real_option['mid']
    else:
        try:
            entry_price = bs_price(S, K, T, R_RISK_FREE, iv, opt_type)
            if entry_price < 0.05:
                return None   # too cheap / far OTM
        except Exception:
            return None

    # Greeks: use real chain data if available, fall back to Black-Scholes
    if real_option and real_option.get('delta'):
        delta = real_option.get('delta', 0.35 if opt_type == 'call' else -0.35)
        theta = real_option.get('theta', -entry_price * 0.01)
        vega  = real_option.get('vega',  entry_price * 0.02)
        gamma = real_option.get('gamma', 0.003)
    else:
        try:
            g     = bs_greeks(S, K, T, R_RISK_FREE, iv, opt_type)
            delta = g['delta']
            theta = g['theta']
            vega  = g['vega']
            gamma = g['gamma']
        except Exception:
            delta = 0.35 if opt_type == 'call' else -0.35
            theta = -entry_price * 0.01
            vega  = entry_price * 0.02
            gamma = 0.003

    # Targets
    try:
        targets = calculate_targets(S, iv, dte, closes, highs, lows, regime, opt_type)
    except Exception:
        em = S * iv * math.sqrt(dte/365)
        targets = {
            'price_target': S + em * 0.7 if opt_type=='call' else S - em * 0.7,
            'stop_loss':    S - em * 0.4 if opt_type=='call' else S + em * 0.4,
        }

    price_target  = targets.get('price_target', S * (1.05 if opt_type=='call' else 0.95))
    # calculate_targets returns 'price_stop' for the stock stop level
    stop_loss     = targets.get('stop_loss', targets.get('price_stop',
                    S * (0.97 if opt_type=='call' else 1.03)))

    # Option target/stop — use the real option's IV when available (more accurate)
    real_iv = (real_option.get('iv') or iv) if real_option else iv
    try:
        opt_target = bs_price(price_target, K, T * 0.6, R_RISK_FREE, real_iv, opt_type)
        opt_stop   = bs_price(stop_loss,    K, T * 0.6, R_RISK_FREE, real_iv * 0.85, opt_type)
    except Exception:
        opt_target = entry_price * 2.0
        opt_stop   = entry_price * 0.50

    # If delta is high (deep ITM), blend BS estimate with delta-based projection
    # which is more reliable for options moving nearly 1:1 with the stock
    if abs(delta) > 0.70:
        stock_gain = abs(price_target - S) * abs(delta)
        stock_loss = abs(stop_loss   - S) * abs(delta)
        delta_target = entry_price + stock_gain
        delta_stop   = entry_price - stock_loss
        opt_target   = (opt_target + delta_target) / 2
        opt_stop     = (opt_stop   + delta_stop)   / 2

    # Hard sanity checks — target at least 20% profit, stop between 25% and 65% loss
    opt_target = max(entry_price * 1.20, opt_target)
    opt_stop   = max(entry_price * 0.35, min(entry_price * 0.75, opt_stop))

    # R:R
    reward = opt_target - entry_price
    risk   = entry_price - opt_stop
    rr     = round(reward / risk, 2) if risk > 0 else 1.0

    # Probabilities
    try:
        direction = 'up' if opt_type == 'call' else 'down'
        p_touch   = prob_touch_before_expiry(S, price_target, T, R_RISK_FREE, iv, direction)
        p_profit  = prob_expire_itm(S, K, T, R_RISK_FREE, iv, opt_type)
    except Exception:
        p_touch  = 0.35
        p_profit = 0.40

    # Breakeven
    breakeven = K + entry_price if opt_type == 'call' else K - entry_price

    # ── Pre-score quality filters ────────────────────────────────────────────
    # Skip options that are so far OTM they have very low probability of success
    if abs(delta) < 0.18:
        return None   # delta too low — very cheap lottery ticket, not a trade

    # Skip when R:R is terrible (risk more than you can realistically make)
    if rr < 1.3:
        return None

    # Skip when probability of touching target is too low
    if p_touch < 0.20:
        return None

    # Skip options that are essentially worthless (< $0.10)
    if entry_price < 0.10:
        return None

    # Score
    score = _score_candidate(S, K, T, iv, opt_type, regime, targets,
                              p_touch, rr, ind, ivr, vix, delta=delta)

    # Filter: minimum quality bar — raised from 35 → 45 for better trade selection
    if score < 45:
        return None

    # Format expiry string — snap to nearest FRIDAY (standard options expiry)
    # Robinhood lists only real exchange expirations (Fridays for weeklies/monthlies)
    from datetime import date, timedelta
    if chain_expiry:
        # Use the real options market expiry date
        exp_date   = date.fromisoformat(chain_expiry)
        actual_dte = (exp_date - date.today()).days
    else:
        _target = date.today() + timedelta(days=dte)
        _dow    = _target.weekday()   # 0=Mon … 4=Fri … 6=Sun
        if _dow <= 4:
            exp_date = _target + timedelta(days=(4 - _dow))
        else:
            exp_date = _target + timedelta(days=(4 - _dow + 7))
        actual_dte = (exp_date - date.today()).days
        if actual_dte < tf['dte_min']:
            exp_date   = exp_date + timedelta(weeks=1)
            actual_dte = (exp_date - date.today()).days
        elif actual_dte > tf['dte_max']:
            exp_date   = exp_date - timedelta(weeks=1)
            actual_dte = (exp_date - date.today()).days

    exp_str = exp_date.strftime('%b %d')

    return {
        'ticker':      ticker,
        'sector':      ticker_data.get('sector', ''),
        'timeframe':   timeframe,
        'option_type': opt_type.upper(),
        'strike':      round(K, 2),
        'expiry':      exp_str,
        'dte':         actual_dte,
        'entry':       round(entry_price, 2),
        'bid':         round(real_option.get('bid', 0) if real_option else 0, 2),
        'ask':         round(real_option.get('ask', 0) if real_option else 0, 2),
        'target':      round(opt_target, 2),
        'stop':        round(opt_stop, 2),
        'rr':          rr,
        'score':       score,
        'p_touch':     round(p_touch * 100, 1),
        'p_profit':    round(p_profit * 100, 1),
        'iv_pct':      round(iv * 100, 1),
        'iv_rank':     round(ivr, 0),
        'delta':       round(abs(delta), 2),
        'theta':       round(theta, 3),
        'vega':        round(vega, 3),
        'rsi':         round(ind.get('rsi', 50), 1),
        'trend':       regime.get('trend', 'sideways').capitalize(),
        'vol_regime':  regime.get('vol_regime', 'normal').capitalize(),
        'price':       round(S, 2),
        'breakeven':   round(breakeven, 2),
        'stock_target':round(price_target, 2),
        # Additional raw data for the detail panel
        'sma20':       round(ind.get('sma20', S), 2),
        'sma50':       round(ind.get('sma50', S), 2),
        'sma200':      round(ind.get('sma200', S), 2),
        'atr':         round(ind.get('atr', 0), 2),
        'macd_val':    round(ind.get('macd', 0), 4),
        'macd_sig':    round(ind.get('signal', 0), 4),
        'bb_upper':    round(ind.get('bb_upper', S*1.02), 2),
        'bb_lower':    round(ind.get('bb_lower', S*0.98), 2),
        'bb_mid':      round(ind.get('bb_mid', S), 2),
        'regime_strength': regime.get('strength', 'moderate'),
        'price_target_stock': round(price_target, 2),
        'stop_loss_stock':    round(stop_loss, 2),
        'gamma':       round(gamma, 6),
        'reasoning':   _build_reasoning(
            ticker=ticker, S=S, K=K, dte=dte, iv=iv, ivr=ivr,
            opt_type=opt_type, regime=regime, ind=ind, vix=vix,
            entry_price=entry_price, opt_target=round(opt_target,2),
            opt_stop=round(opt_stop,2), price_target=price_target,
            stop_loss=stop_loss, breakeven=breakeven,
            p_touch=p_touch, p_profit=p_profit, rr=rr, score=score,
            delta=delta, theta=theta, vega=vega, gamma=gamma,
        ),
    }


def scan_all(universe: dict, vix: float = 18.0, top_n: int = 20):
    """
    Scan every ticker in universe for all 3 timeframes.
    Returns dict: { timeframe: [sorted candidates] }
    """
    results = {tf: [] for tf in TIMEFRAMES}

    total = len(universe)
    for i, (sym, data) in enumerate(universe.items()):
        if (i+1) % 20 == 0 or (i+1) == total:
            print(f"  Scanning... {i+1}/{total}", flush=True)

        for tf in TIMEFRAMES:
            try:
                candidate = scan_ticker(data, tf, vix)
                if candidate:
                    results[tf].append(candidate)
            except Exception:
                continue

    # Sort by score descending, keep top_n
    for tf in TIMEFRAMES:
        results[tf] = sorted(results[tf], key=lambda x: -x['score'])[:top_n]

    return results
