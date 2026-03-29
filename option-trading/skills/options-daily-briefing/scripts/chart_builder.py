"""
Chart Builder for Daily Options Briefing
==========================================
Generates base64-encoded PNG charts to embed in the HTML dashboard.
Charts per trade recommendation:
  1. Price chart with technical indicators (SMA, Bollinger, RSI, MACD, volume)
  2. P&L diagram for the recommended option at expiry
  3. Probability distribution (normal curve, showing target vs stop)
"""

import math, io, base64
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import matplotlib.ticker as mticker
from matplotlib.patches import FancyBboxPatch

from analysis_engine import (bs_greeks, bs_price, sma, ema, rsi, macd,
                               bollinger_bands, expected_move, norm_cdf)

# ─── Style ─────────────────────────────────────────────────────────────────────
BG     = '#0d1117'
PANEL  = '#161b22'
BORDER = '#30363d'
TEXT   = '#c9d1d9'
MUTED  = '#8b949e'
GREEN  = '#3fb950'
RED    = '#f85149'
BLUE   = '#58a6ff'
AMBER  = '#e3b341'
PURPLE = '#bc8cff'
TEAL   = '#39d353'
ORANGE = '#ffa657'

plt.rcParams.update({
    'figure.facecolor':  BG,
    'axes.facecolor':    PANEL,
    'axes.edgecolor':    BORDER,
    'axes.labelcolor':   TEXT,
    'axes.titlecolor':   TEXT,
    'axes.grid':         True,
    'grid.color':        BORDER,
    'grid.linewidth':    0.5,
    'grid.alpha':        0.6,
    'xtick.color':       MUTED,
    'ytick.color':       MUTED,
    'text.color':        TEXT,
    'legend.facecolor':  PANEL,
    'legend.edgecolor':  BORDER,
    'legend.labelcolor': TEXT,
    'figure.dpi':        120,
    'text.usetex':       False,
    'mathtext.default':  'regular',
    'font.family':       'DejaVu Sans',
})


def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight',
                facecolor=BG, edgecolor='none', dpi=120)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return b64


# ─── 1. Price Chart with Indicators ──────────────────────────────────────────

def price_chart(dates, opens, highs, lows, closes, volumes, rec, max_bars=90):
    """
    Full technical analysis chart:
    - Candlestick OHLC
    - SMA 20, 50, 200
    - Bollinger Bands
    - Volume bars (colored by up/down)
    - RSI panel
    - MACD panel
    - Annotations: target, stop, key levels
    """
    # Trim to max_bars for clarity
    n = min(len(closes), max_bars)
    dates_p  = dates[-n:]
    opens_p  = opens[-n:];  highs_p  = highs[-n:]
    lows_p   = lows[-n:];   closes_p = closes[-n:]
    volumes_p = volumes[-n:]

    xs = list(range(n))

    # Indicators (on full data, trim at end)
    s20  = [v for v in sma(closes, 20)][-n:]
    s50  = [v for v in sma(closes, 50)][-n:]
    s200 = [v for v in sma(closes, 200)][-n:]
    bb   = [v for v in bollinger_bands(closes, 20)][-n:]
    rsi_v = [v for v in rsi(closes)][-n:]
    macd_line, sig_line, hist_line = macd(closes)
    macd_v  = macd_line[-n:]
    sigv    = sig_line[-n:]
    histv   = hist_line[-n:]

    # Figure layout: price | volume | rsi | macd
    fig = plt.figure(figsize=(13, 9))
    gs = gridspec.GridSpec(4, 1, figure=fig,
                            height_ratios=[5, 1.2, 1.5, 1.5],
                            hspace=0.05)

    ax_price  = fig.add_subplot(gs[0])
    ax_vol    = fig.add_subplot(gs[1], sharex=ax_price)
    ax_rsi    = fig.add_subplot(gs[2], sharex=ax_price)
    ax_macd   = fig.add_subplot(gs[3], sharex=ax_price)

    # ── Price panel ───────────────────────────────────────────────────────────
    # Candlesticks
    for i, (o, h, l, c) in enumerate(zip(opens_p, highs_p, lows_p, closes_p)):
        color = GREEN if c >= o else RED
        # Body
        ax_price.bar(i, abs(c - o), bottom=min(c, o), color=color, alpha=0.85,
                     width=0.6, linewidth=0)
        # Wick
        ax_price.plot([i, i], [l, h], color=color, linewidth=0.8, alpha=0.9)

    # Moving averages
    def plot_indicator(ax, xs, vals, color, label, lw=1.4, ls='-'):
        pairs = [(x, v) for x, v in zip(xs, vals) if v is not None]
        if pairs:
            px, pv = zip(*pairs)
            ax.plot(px, pv, color=color, linewidth=lw, linestyle=ls, label=label, alpha=0.85)

    plot_indicator(ax_price, xs, s20,  BLUE,   '20 SMA',  1.4)
    plot_indicator(ax_price, xs, s50,  AMBER,  '50 SMA',  1.5)
    plot_indicator(ax_price, xs, s200, PURPLE, '200 SMA', 1.2, ls='--')

    # Bollinger Bands
    bb_lower = [v[0] for v in bb]; bb_mid = [v[1] for v in bb]; bb_upper = [v[2] for v in bb]
    valid_bb = [(x, l, u) for x, l, u in zip(xs, bb_lower, bb_upper) if l is not None and u is not None]
    if valid_bb:
        bx, bl, bu = zip(*valid_bb)
        ax_price.fill_between(bx, bl, bu, alpha=0.07, color=BLUE, label='BB (2σ)')
        ax_price.plot(bx, bl, color=BLUE, linewidth=0.6, alpha=0.4, linestyle=':')
        ax_price.plot(bx, bu, color=BLUE, linewidth=0.6, alpha=0.4, linestyle=':')

    # Target and stop lines
    ax_price.axhline(rec['price_target'], color=GREEN, linewidth=1.8, linestyle='--', alpha=0.9,
                     label=f"Target {rec['price_target']:.2f}")
    ax_price.axhline(rec['price_stop'],   color=RED,   linewidth=1.5, linestyle='--', alpha=0.9,
                     label=f"Stop {rec['price_stop']:.2f}")
    ax_price.axhline(rec['current_price'], color=AMBER, linewidth=1.2, linestyle=':', alpha=0.7,
                     label=f"Current {rec['current_price']:.2f}")

    # Annotate target and stop
    ax_price.annotate(f" TARGET {rec['price_target']:.2f}",
                      xy=(n - 1, rec['price_target']), xytext=(n - 0.5, rec['price_target']),
                      fontsize=9, color=GREEN, fontweight='bold', va='center')
    ax_price.annotate(f" STOP {rec['price_stop']:.2f}",
                      xy=(n - 1, rec['price_stop']), xytext=(n - 0.5, rec['price_stop']),
                      fontsize=9, color=RED, fontweight='bold', va='center')

    ax_price.set_ylabel('Price ($)', fontsize=10, color=TEXT)
    ax_price.set_title(
        f"{rec['ticker']} — {rec['timeframe'].upper()} TERM  |  {rec['opt_type']} {rec['strike']}  "
        f"|  Entry: ${rec['entry_price']:.2f}  |  Target: ${rec['price_target']:.2f}  "
        f"|  Prob: {rec['prob_touch']:.0f}%",
        fontsize=11, fontweight='bold', pad=10, color=TEXT
    )
    ax_price.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f'${y:.0f}'))
    ax_price.legend(loc='upper left', fontsize=8, framealpha=0.7, ncol=4)
    plt.setp(ax_price.get_xticklabels(), visible=False)

    # ── Volume panel ──────────────────────────────────────────────────────────
    vol_colors = [GREEN if c >= o else RED for c, o in zip(closes_p, opens_p)]
    ax_vol.bar(xs, volumes_p, color=vol_colors, alpha=0.7, width=0.7)
    # Volume SMA
    vol_sma = sma(volumes_p, 10)
    plot_indicator(ax_vol, xs, vol_sma, AMBER, 'Vol SMA', 1.2)
    ax_vol.set_ylabel('Volume', fontsize=8, color=MUTED)
    ax_vol.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda y, _: f'{y/1e6:.1f}M' if y >= 1e6 else f'{y/1e3:.0f}K'))
    plt.setp(ax_vol.get_xticklabels(), visible=False)

    # ── RSI panel ─────────────────────────────────────────────────────────────
    valid_rsi = [(x, v) for x, v in zip(xs, rsi_v) if v is not None]
    if valid_rsi:
        rx, rv = zip(*valid_rsi)
        ax_rsi.plot(rx, rv, color=PURPLE, linewidth=1.5, label='RSI 14')
        ax_rsi.fill_between(rx, rv, 70, where=[v > 70 for v in rv], alpha=0.2, color=RED)
        ax_rsi.fill_between(rx, rv, 30, where=[v < 30 for v in rv], alpha=0.2, color=GREEN)
    ax_rsi.axhline(70, color=RED,   linewidth=0.8, linestyle='--', alpha=0.7)
    ax_rsi.axhline(50, color=MUTED, linewidth=0.6, linestyle=':', alpha=0.5)
    ax_rsi.axhline(30, color=GREEN, linewidth=0.8, linestyle='--', alpha=0.7)
    ax_rsi.set_ylim(0, 100)
    ax_rsi.set_ylabel('RSI', fontsize=8, color=MUTED)
    ax_rsi.legend(loc='upper left', fontsize=7, framealpha=0.7)
    plt.setp(ax_rsi.get_xticklabels(), visible=False)

    # ── MACD panel ────────────────────────────────────────────────────────────
    valid_hist = [(x, v) for x, v in zip(xs, histv) if v is not None]
    if valid_hist:
        hx, hv = zip(*valid_hist)
        bar_colors = [GREEN if v >= 0 else RED for v in hv]
        ax_macd.bar(hx, hv, color=bar_colors, alpha=0.7, width=0.7)
    plot_indicator(ax_macd, xs, macd_v,  BLUE,  'MACD',   1.3)
    plot_indicator(ax_macd, xs, sigv,    AMBER, 'Signal', 1.3)
    ax_macd.axhline(0, color=BORDER, linewidth=0.8)
    ax_macd.set_ylabel('MACD', fontsize=8, color=MUTED)
    ax_macd.legend(loc='upper left', fontsize=7, framealpha=0.7, ncol=2)

    # X axis: show date labels
    step = max(1, n // 10)
    tick_positions = list(range(0, n, step))
    tick_labels    = [dates_p[i] if i < len(dates_p) else '' for i in tick_positions]
    ax_macd.set_xticks(tick_positions)
    ax_macd.set_xticklabels(tick_labels, rotation=30, ha='right', fontsize=8)

    fig.tight_layout(rect=[0, 0, 1, 0.99])
    return fig_to_base64(fig)


# ─── 2. P&L Diagram ──────────────────────────────────────────────────────────

def pnl_chart(rec, r=0.05):
    """P&L diagram for the recommended option at expiry, with current-time P&L overlay."""
    S     = rec['current_price']
    K     = rec['strike']
    T     = rec['dte'] / 365.0
    iv    = rec['iv'] / 100.0
    opt   = rec['opt_type'].lower()
    prem  = rec['entry_price']

    spread = max(abs(S - K) * 2.5, S * 0.12)
    prices = np.linspace(S - spread, S + spread, 300)

    # P&L at expiry
    pnl_expiry = np.array([
        (max(p - K, 0) if opt == 'call' else max(K - p, 0)) - prem
        for p in prices
    ]) * 100  # per contract

    # P&L at half-time (current option value vs entry)
    T_half = max(T / 2, 0.01)
    pnl_now = np.array([
        bs_price(p, K, T_half, r, iv, opt) - prem
        for p in prices
    ]) * 100

    fig, ax = plt.subplots(figsize=(7, 4.5))

    ax.axhline(0, color=BORDER, linewidth=1, linestyle='--', alpha=0.7)
    ax.axvline(S, color=AMBER, linewidth=1.5, linestyle=':', alpha=0.8,
               label=f'Current {S:.2f}')

    # Fill profit/loss
    ax.fill_between(prices, pnl_expiry, 0, where=(pnl_expiry >= 0),
                    alpha=0.18, color=GREEN)
    ax.fill_between(prices, pnl_expiry, 0, where=(pnl_expiry < 0),
                    alpha=0.18, color=RED)

    # Lines
    ax.plot(prices, pnl_expiry, color=GREEN, linewidth=2.2, label='P&L at Expiry')
    ax.plot(prices, pnl_now,    color=BLUE,  linewidth=1.5, linestyle='--',
            label=f'P&L at ~{rec["dte"]//2}DTE (mid-trade)')

    # Target line
    ax.axvline(rec['price_target'], color=GREEN, linewidth=1.5, linestyle='--', alpha=0.9,
               label=f"Target ${rec['price_target']:.2f}")
    ax.axvline(rec['price_stop'],   color=RED,   linewidth=1.2, linestyle='--', alpha=0.9,
               label=f"Stop ${rec['price_stop']:.2f}")

    # Annotations
    target_pnl = (bs_price(rec['price_target'], K, T_half, r, iv, opt) - prem) * 100
    ax.annotate(f"+${target_pnl:.0f}\nper contract",
                xy=(rec['price_target'], target_pnl),
                xytext=(rec['price_target'] + S * 0.02, target_pnl * 0.8),
                fontsize=8, color=GREEN, fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=GREEN, lw=1))

    ax.set_xlabel('Stock Price', fontsize=10)
    ax.set_ylabel('Profit / Loss per Contract ($)', fontsize=10)
    ax.set_title(f'P&L Diagram — {rec["option_label"]}', fontsize=11, fontweight='bold')
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:.0f}'))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f'${y:,.0f}'))
    ax.legend(loc='upper left' if opt == 'call' else 'upper right',
              fontsize=8, framealpha=0.8)

    fig.tight_layout()
    return fig_to_base64(fig)


# ─── 3. Probability Distribution Chart ───────────────────────────────────────

def probability_chart(rec, r=0.05):
    """
    Log-normal distribution of possible stock prices at expiry.
    Shows: target, stop, breakeven, current price, colored zones.
    """
    S   = rec['current_price']
    iv  = rec['iv'] / 100.0
    T   = rec['dte'] / 365.0
    opt = rec['opt_type'].lower()
    K   = rec['strike']
    prem = rec['entry_price']

    # Log-normal distribution parameters
    mu    = math.log(S) + (r - 0.5 * iv**2) * T
    sigma = iv * math.sqrt(T)

    # Price range: 3 sigmas either side
    lo = S * math.exp(-3 * sigma)
    hi = S * math.exp( 3 * sigma)
    prices = np.linspace(lo, hi, 500)

    # PDF
    pdf = np.array([
        math.exp(-0.5 * ((math.log(p) - mu) / sigma)**2) / (p * sigma * math.sqrt(2 * math.pi))
        for p in prices
    ])
    pdf = pdf / pdf.max()  # normalize to 1

    target = rec['price_target']
    stop   = rec['price_stop']
    breakeven = K + prem if opt == 'call' else K - prem

    fig, ax = plt.subplots(figsize=(7, 4))

    # Fill zones
    if opt == 'call':
        ax.fill_between(prices, pdf, 0,
                        where=(prices >= breakeven),
                        alpha=0.25, color=GREEN, label=f'Profitable zone (>{breakeven:.2f})')
        ax.fill_between(prices, pdf, 0,
                        where=(prices < breakeven),
                        alpha=0.20, color=RED, label=f'Loss zone (<{breakeven:.2f})')
        ax.fill_between(prices, pdf, 0,
                        where=(prices >= target),
                        alpha=0.35, color=TEAL, label=f'Target zone (>{target:.2f})')
    else:
        ax.fill_between(prices, pdf, 0,
                        where=(prices <= breakeven),
                        alpha=0.25, color=GREEN, label=f'Profitable zone (<{breakeven:.2f})')
        ax.fill_between(prices, pdf, 0,
                        where=(prices > breakeven),
                        alpha=0.20, color=RED, label=f'Loss zone (>{breakeven:.2f})')
        ax.fill_between(prices, pdf, 0,
                        where=(prices <= target),
                        alpha=0.35, color=TEAL, label=f'Target zone (<{target:.2f})')

    # Main distribution
    ax.plot(prices, pdf, color=BLUE, linewidth=2.5, label='Price distribution at expiry')

    # Key verticals
    for val, color, lbl in [
        (S,          AMBER,  f'Now {S:.2f}'),
        (breakeven,  GREEN,  f'Breakeven {breakeven:.2f}'),
        (target,     TEAL,   f'Target {target:.2f}'),
        (stop,       RED,    f'Stop {stop:.2f}'),
    ]:
        if lo < val < hi:
            ax.axvline(val, color=color, linewidth=1.5, linestyle='--', alpha=0.9, label=lbl)

    # Probability annotations
    ax.text(0.02, 0.96,
            f"P(touch target): {rec['prob_touch']:.0f}%\n"
            f"P(profit at expiry): {rec['prob_profit']:.0f}%\n"
            f"P(ITM at expiry): {rec['prob_itm']:.0f}%",
            transform=ax.transAxes, va='top', ha='left', fontsize=9,
            color=TEXT, fontfamily='monospace',
            bbox=dict(boxstyle='round,pad=0.4', facecolor=PANEL, edgecolor=BORDER))

    ax.set_xlabel('Stock Price at Expiry', fontsize=10)
    ax.set_ylabel('Relative Probability', fontsize=10)
    ax.set_title(f'Probability Distribution — {rec["dte"]} DTE  |  IV {rec["iv"]:.0f}%',
                 fontsize=11, fontweight='bold')
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:.0f}'))
    ax.set_yticks([])
    ax.legend(loc='upper right', fontsize=7.5, framealpha=0.8, ncol=2)

    fig.tight_layout()
    return fig_to_base64(fig)


# ─── 4. Market Overview Mini-Chart ───────────────────────────────────────────

def market_overview_chart(market_data):
    """
    Compact multi-panel showing SPY/QQQ/VIX overview.
    market_data: list of {label, closes, color}
    """
    n_panels = len(market_data)
    fig, axes = plt.subplots(1, n_panels, figsize=(4 * n_panels, 2.5))
    if n_panels == 1:
        axes = [axes]

    for ax, md in zip(axes, market_data):
        closes = md['closes']
        xs = range(len(closes))
        color = md.get('color', BLUE)
        change = (closes[-1] - closes[0]) / closes[0] * 100
        trend_color = GREEN if change >= 0 else RED

        ax.plot(xs, closes, color=trend_color, linewidth=2)
        ax.fill_between(xs, closes, closes[0], alpha=0.15, color=trend_color)
        ax.axhline(closes[0], color=BORDER, linewidth=0.7, linestyle=':')

        sign = '+' if change >= 0 else ''
        ax.set_title(f"{md['label']}\n{closes[-1]:.2f} ({sign}{change:.1f}%)",
                     fontsize=10, fontweight='bold',
                     color=trend_color)
        ax.set_yticks([]); ax.set_xticks([])
        for spine in ax.spines.values():
            spine.set_color(BORDER)

    fig.tight_layout(pad=0.5)
    return fig_to_base64(fig)
