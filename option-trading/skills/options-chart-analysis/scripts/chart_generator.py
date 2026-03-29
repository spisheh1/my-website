"""
Options Chart Generator Script (matplotlib version)
====================================================
Generates professional options trading charts as PNG files.
Requires only matplotlib (pre-installed).

Usage examples:
  python chart_generator.py --chart pnl --output /path/to/out.png --params '{"strategy":"iron_condor","underlying":505,"short_put":480,"long_put":470,"short_call":530,"long_call":540,"credit":3.50}'
  python chart_generator.py --chart iv_smile --output /path/to/out.png --params '{"strikes":[460,470,480,490,500,510,520,530,540],"ivs":[0.32,0.28,0.25,0.22,0.20,0.21,0.23,0.26,0.30],"underlying":500,"expiry":"Apr 18"}'
  python chart_generator.py --chart greeks --output /path/to/out.png --params '{"option_type":"call","strike":500,"underlying":505,"dte":30,"iv":0.25}'
  python chart_generator.py --chart oi_heatmap --output /path/to/out.png --params '{"strikes":[480,490,500,510,520],"call_oi":[3400,8900,12000,9500,4200],"put_oi":[11000,14500,10200,5400,2800],"underlying":505}'
  python chart_generator.py --chart theta_decay --output /path/to/out.png --params '{"strike":195,"underlying":195,"iv":0.22,"dte_max":60}'
  python chart_generator.py --chart iv_history --output /path/to/out.png --params '{"ticker":"AAPL","dates":["Jan","Feb","Mar","Apr","May","Jun"],"iv":[0.22,0.25,0.35,0.28,0.24,0.30],"rv":[0.18,0.22,0.30,0.24,0.20,0.27]}'
  python chart_generator.py --chart multi_pnl --output /path/to/out.png --params '{"strategies":[{"name":"Iron Condor","short_put":480,"long_put":470,"short_call":530,"long_call":540,"credit":3.50},{"name":"Bull Put Spread","short_put":490,"long_put":480,"credit":2.00}],"underlying":505}'
"""

import json
import sys
import math
import argparse
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import matplotlib.ticker as mticker
import numpy as np

# ── Style constants ────────────────────────────────────────────────────────────
BG      = '#111827'
PANEL   = '#1f2937'
TEXT    = '#e0e0e0'
GRID    = '#374151'
GREEN   = '#00c853'
RED     = '#ef5350'
BLUE    = '#00bcd4'
AMBER   = '#FFC107'
PURPLE  = '#ab47bc'
ORANGE  = '#ff7043'

def mt(s):
    """Escape dollar signs for matplotlib titles/labels."""
    return s.replace('$', r'\$')

plt.rcParams.update({
    'text.usetex': False,
    'mathtext.default': 'regular',
    'figure.facecolor':   BG,
    'axes.facecolor':     BG,
    'axes.edgecolor':     GRID,
    'axes.labelcolor':    TEXT,
    'axes.titlecolor':    TEXT,
    'axes.grid':          True,
    'grid.color':         GRID,
    'grid.linewidth':     0.6,
    'grid.alpha':         0.7,
    'xtick.color':        TEXT,
    'ytick.color':        TEXT,
    'text.color':         TEXT,
    'legend.facecolor':   PANEL,
    'legend.edgecolor':   GRID,
    'legend.labelcolor':  TEXT,
    'figure.dpi':         140,
    'font.family':        'DejaVu Sans',
})

# ── Black-Scholes ──────────────────────────────────────────────────────────────

def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def norm_pdf(x):
    return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)

def bs_price(S, K, T, r, sigma, opt='call'):
    if T <= 0:
        return max(S-K,0) if opt=='call' else max(K-S,0)
    d1 = (math.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*math.sqrt(T))
    d2 = d1 - sigma*math.sqrt(T)
    if opt == 'call':
        return S*norm_cdf(d1) - K*math.exp(-r*T)*norm_cdf(d2)
    return K*math.exp(-r*T)*norm_cdf(-d2) - S*norm_cdf(-d1)

def bs_greeks(S, K, T, r, sigma, opt='call'):
    if T <= 0:
        return {'delta':1.0 if (opt=='call' and S>K) else 0.0,'gamma':0,'theta':0,'vega':0,'price':bs_price(S,K,T,r,sigma,opt)}
    d1 = (math.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*math.sqrt(T))
    d2 = d1 - sigma*math.sqrt(T)
    delta = norm_cdf(d1) if opt=='call' else norm_cdf(d1)-1
    gamma = norm_pdf(d1) / (S*sigma*math.sqrt(T))
    vega  = S*norm_pdf(d1)*math.sqrt(T)/100
    th_raw= (-(S*norm_pdf(d1)*sigma)/(2*math.sqrt(T))
             - r*K*math.exp(-r*T)*(norm_cdf(d2) if opt=='call' else norm_cdf(-d2)))
    return {'delta':delta,'gamma':gamma,'theta':th_raw/365,'vega':vega,
            'price':bs_price(S,K,T,r,sigma,opt)}

# ── Helpers ────────────────────────────────────────────────────────────────────

def save(fig, path):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    fig.savefig(path, bbox_inches='tight', facecolor=BG, dpi=140)
    plt.close(fig)
    print(json.dumps({'output': path, 'status': 'ok'}))

def leg_pnl(leg, price):
    k, q, prem = leg['strike'], leg['qty'], leg.get('premium', 0)
    intrinsic = max(price-k,0) if leg['type']=='call' else max(k-price,0)
    return q*(intrinsic - prem)*100

def build_legs(params):
    strategy = params.get('strategy','custom')
    legs = params.get('legs', [])
    credit = params.get('credit', 0)
    if strategy == 'iron_condor' and not legs:
        sp,lp,sc,lc = params['short_put'],params['long_put'],params['short_call'],params['long_call']
        cr = params.get('credit',3.0)
        legs = [{'type':'put','strike':sp,'qty':-1,'premium':cr*0.5},
                {'type':'put','strike':lp,'qty': 1,'premium':0},
                {'type':'call','strike':sc,'qty':-1,'premium':cr*0.5},
                {'type':'call','strike':lc,'qty': 1,'premium':0}]
        credit = cr
    elif strategy == 'bull_put_spread' and not legs:
        sp,lp = params['short_put'],params['long_put']
        cr = params.get('credit',2.0)
        legs = [{'type':'put','strike':sp,'qty':-1,'premium':cr},
                {'type':'put','strike':lp,'qty': 1,'premium':0}]
        credit = cr
    elif strategy == 'bear_call_spread' and not legs:
        sc,lc = params['short_call'],params['long_call']
        cr = params.get('credit',2.0)
        legs = [{'type':'call','strike':sc,'qty':-1,'premium':cr},
                {'type':'call','strike':lc,'qty': 1,'premium':0}]
        credit = cr
    elif strategy == 'long_call' and not legs:
        legs = [{'type':'call','strike':params['strike'],'qty':1,'premium':params['premium']}]
        credit = -params['premium']
    elif strategy == 'long_put' and not legs:
        legs = [{'type':'put','strike':params['strike'],'qty':1,'premium':params['premium']}]
        credit = -params['premium']
    elif strategy == 'bull_call_spread' and not legs:
        legs = [{'type':'call','strike':params['long_strike'],'qty':1,'premium':params['long_premium']},
                {'type':'call','strike':params['short_strike'],'qty':-1,'premium':params['short_premium']}]
        credit = params['short_premium']-params['long_premium']
    elif strategy == 'long_straddle' and not legs:
        legs = [{'type':'call','strike':params['strike'],'qty':1,'premium':params['call_premium']},
                {'type':'put','strike':params['strike'],'qty':1,'premium':params['put_premium']}]
        credit = -(params['call_premium']+params['put_premium'])
    elif strategy == 'covered_call' and not legs:
        legs = [{'type':'call','strike':params['strike'],'qty':-1,'premium':params['premium']}]
        credit = params['premium']
    return legs, credit

# ── Chart Functions ────────────────────────────────────────────────────────────

def chart_pnl(params, output_path):
    legs, credit = build_legs(params)
    underlying   = params.get('underlying', 100)
    strategy     = params.get('strategy','custom').replace('_',' ').title()

    strikes = [l['strike'] for l in legs]
    center  = underlying
    spread  = max(max(strikes)-min(strikes), underlying*0.15)*1.6
    prices  = np.linspace(center-spread, center+spread, 400)
    pnl     = np.array([sum(leg_pnl(l,p) for l in legs) for p in prices])

    max_profit = float(pnl.max())
    max_loss   = float(pnl.min())
    breakevens = [prices[i] for i in range(1,len(prices))
                  if (pnl[i-1] < 0) != (pnl[i] < 0)]

    fig, ax = plt.subplots(figsize=(11, 6))

    # Fill profit/loss areas
    ax.fill_between(prices, pnl, 0, where=(pnl>=0), alpha=0.20, color=GREEN, label='Profit zone')
    ax.fill_between(prices, pnl, 0, where=(pnl<0),  alpha=0.20, color=RED,   label='Loss zone')

    # P&L line
    ax.plot(prices, pnl, color=BLUE, lw=2.5, label='P&L at expiry', zorder=5)

    # Zero line
    ax.axhline(0, color=GRID, lw=1.2, ls='--')

    # Current price
    ax.axvline(underlying, color=AMBER, lw=2, ls=':', label=f'Current price: {underlying}', zorder=6)

    # Strike lines
    for l in legs:
        col = GREEN if l['qty']>0 else RED
        lbl = f"{'Long' if l['qty']>0 else 'Short'} {l['type'].capitalize()} ${l['strike']}"
        ax.axvline(l['strike'], color=col, lw=1.2, ls='--', alpha=0.7, label=lbl)

    # Breakevens
    for be in breakevens:
        ax.axvline(be, color='white', lw=1, ls=':', alpha=0.5)
        ax.annotate(f'BE: {be:.1f}', xy=(be, 0), xytext=(be+underlying*0.005, max_profit*0.25),
                    color='white', fontsize=8, ha='left')

    # Annotations
    ax.annotate(f'Max Profit: {max_profit:,.0f}',
                xy=(0.02,0.97), xycoords='axes fraction', va='top',
                color=GREEN, fontsize=11, fontweight='bold')
    ax.annotate(f'Max Loss:   {max_loss:,.0f}',
                xy=(0.02,0.90), xycoords='axes fraction', va='top',
                color=RED, fontsize=11, fontweight='bold')
    credit_lbl = f"{'Credit' if credit>0 else 'Debit'}: {abs(credit):.2f}/share"
    ax.annotate(credit_lbl,
                xy=(0.02,0.83), xycoords='axes fraction', va='top',
                color=AMBER, fontsize=10)

    ax.set_xlabel('Stock Price at Expiration ($)', fontsize=12)
    ax.set_ylabel('Profit / Loss ($)', fontsize=12)
    ax.set_title(f'P&L Diagram — {strategy}', fontsize=15, fontweight='bold', pad=14)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'${x:.0f}'))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y,_: f'${y:,.0f}'))
    ax.legend(loc='upper right', fontsize=9, framealpha=0.8)
    fig.tight_layout()
    save(fig, output_path)
    return {'max_profit': max_profit, 'max_loss': max_loss, 'breakevens': breakevens}


def chart_iv_smile(params, output_path):
    strikes    = params['strikes']
    raw_ivs    = params['ivs']
    ivs        = [v*100 if v<5 else v for v in raw_ivs]
    underlying = params.get('underlying', strikes[len(strikes)//2])
    expiry     = params.get('expiry', '')

    atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i]-underlying))
    atm_iv  = ivs[atm_idx]
    skew    = ivs[0] - ivs[-1]

    fig, ax = plt.subplots(figsize=(10, 5.5))

    ax.plot(strikes, ivs, color=BLUE, lw=2.5, marker='o', ms=7, label='Implied Volatility')
    ax.scatter([strikes[atm_idx]], [atm_iv], color=AMBER, s=120, zorder=6, label=f'ATM IV {atm_iv:.1f}pct')
    ax.axvline(underlying, color=AMBER, lw=1.5, ls=':', alpha=0.8, label=f'Underlying {underlying}')

    # Shade put-skew region
    ax.fill_betweenx([min(ivs)-1, max(ivs)+2],
                     strikes[0], strikes[atm_idx],
                     alpha=0.07, color=RED, label='Put wing (high skew)')
    ax.fill_betweenx([min(ivs)-1, max(ivs)+2],
                     strikes[atm_idx], strikes[-1],
                     alpha=0.07, color=GREEN, label='Call wing')

    skew_txt = f"Put Skew: {skew:+.1f}% vs calls"
    skew_col = RED if skew > 3 else AMBER if skew > 0 else GREEN
    ax.annotate(skew_txt, xy=(0.97, 0.97), xycoords='axes fraction',
                ha='right', va='top', color=skew_col, fontsize=11, fontweight='bold')
    ax.annotate(f'ATM IV: {atm_iv:.1f}%', xy=(0.97, 0.90), xycoords='axes fraction',
                ha='right', va='top', color=AMBER, fontsize=11)

    ax.set_xlabel('Strike Price ($)', fontsize=12)
    ax.set_ylabel('Implied Volatility (%)', fontsize=12)
    title = f'IV Smile / Skew{(" — " + expiry) if expiry else ""}'
    ax.set_title(title, fontsize=15, fontweight='bold', pad=14)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'${x:.0f}'))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y,_: f'{y:.1f}%'))
    ax.legend(fontsize=9, framealpha=0.8)
    fig.tight_layout()
    save(fig, output_path)
    return {'atm_iv': atm_iv, 'put_skew': skew}


def chart_greeks(params, output_path):
    K   = params['strike']
    S0  = params.get('underlying', K)
    dte = params.get('dte', 30)
    iv  = params.get('iv', 0.25)
    r   = params.get('r', 0.05)
    opt = params.get('option_type', 'call')
    T   = dte/365.0

    spread = K*0.20
    prices = np.linspace(K-spread, K+spread, 300)
    gs     = [bs_greeks(S,K,T,r,iv,opt) for S in prices]

    fig = plt.figure(figsize=(14, 10))
    gs_layout = GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.38)

    items = [
        ('Option Price',    [g['price'] for g in gs],  BLUE,   '$'),
        ('Delta (Δ)',        [g['delta'] for g in gs],  GREEN,  ''),
        ('Gamma (Γ)',        [g['gamma'] for g in gs],  PURPLE, ''),
        ('Theta (Θ/day)',    [g['theta'] for g in gs],  RED,    '$'),
        ('Vega (ν/1%IV)',    [g['vega']  for g in gs],  BLUE,   '$'),
    ]

    cg = bs_greeks(S0,K,T,r,iv,opt)

    for idx,(title, vals, color, prefix) in enumerate(items):
        row, col = divmod(idx, 3)
        ax = fig.add_subplot(gs_layout[row, col])
        ax.plot(prices, vals, color=color, lw=2.2)
        ax.axvline(S0, color=AMBER, lw=1.5, ls=':', label=f'S=${S0}')
        ax.axhline(0, color=GRID, lw=0.8, ls='--')
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_xlabel('Stock Price ($)', fontsize=9)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'${x:.0f}'))
        if prefix=='$':
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y,_: f'${y:.3f}'))
        ax.legend(fontsize=8, framealpha=0.7)

    # 6th panel: summary table
    ax6 = fig.add_subplot(gs_layout[1, 2])
    ax6.axis('off')
    table_data = [
        ['Metric', 'Value'],
        ['Price',  f"${cg['price']:.3f}"],
        ['Delta',  f"{cg['delta']:+.4f}"],
        ['Gamma',  f"{cg['gamma']:.5f}"],
        ['Theta',  f"${cg['theta']:.4f}/day"],
        ['Vega',   f"${cg['vega']:.4f}/1%"],
    ]
    tbl = ax6.table(cellText=table_data[1:], colLabels=table_data[0],
                    loc='center', cellLoc='center')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    for (r2,c2), cell in tbl.get_celld().items():
        cell.set_facecolor(PANEL)
        cell.set_edgecolor(GRID)
        cell.set_text_props(color=TEXT)
    ax6.set_title('Current Greeks', fontsize=11, fontweight='bold', pad=8)

    fig.suptitle(
        f'Greeks Dashboard  —  {opt.capitalize()}  Strike {K}  |  {dte} DTE  |  IV {iv*100:.0f}pct  |  Stock {S0}',
        fontsize=14, fontweight='bold', y=1.01
    )
    save(fig, output_path)
    return {'current_greeks': cg}


def chart_oi_heatmap(params, output_path):
    strikes  = np.array(params['strikes'])
    call_oi  = np.array(params['call_oi'], dtype=float)
    put_oi   = np.array(params['put_oi'],  dtype=float)
    call_vol = np.array(params.get('call_volume', [0]*len(strikes)), dtype=float)
    put_vol  = np.array(params.get('put_volume',  [0]*len(strikes)), dtype=float)
    underlying = params.get('underlying', int(strikes[len(strikes)//2]))
    expiry     = params.get('expiry','')
    has_vol    = call_vol.any() or put_vol.any()

    # Max pain
    pain = [sum(max(t-k,0)*c+max(k-t,0)*p for k,c,p in zip(strikes,call_oi,put_oi)) for t in strikes]
    mp   = int(strikes[int(np.argmin(pain))])
    pcr  = float(put_oi.sum()/call_oi.sum()) if call_oi.sum()>0 else 0

    rows  = 2 if has_vol else 1
    fig, axes = plt.subplots(rows, 1, figsize=(12, 5*rows))
    if rows == 1:
        axes = [axes]

    width = (strikes[1]-strikes[0])*0.38 if len(strikes)>1 else 2

    # OI subplot
    ax0 = axes[0]
    ax0.bar(strikes-width*0.5, call_oi, width=width, color=GREEN, alpha=0.85, label='Call OI', zorder=3)
    ax0.bar(strikes+width*0.5, put_oi,  width=width, color=RED,   alpha=0.85, label='Put OI',  zorder=3)
    ax0.axvline(underlying, color=AMBER, lw=2, ls=':', label=f'Current price: {underlying}')
    ax0.axvline(mp,          color=PURPLE, lw=2, ls='--', label=f'Max Pain {mp}')
    ax0.set_xlabel('Strike Price ($)', fontsize=11)
    ax0.set_ylabel('Open Interest', fontsize=11)
    ax0.set_title(f'Open Interest by Strike{" — "+expiry if expiry else ""}\n'
                  f'P/C Ratio: {pcr:.2f}  |  Max Pain: ${mp}', fontsize=12, fontweight='bold')
    ax0.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'${x:.0f}'))
    ax0.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y,_: f'{y/1000:.0f}k' if y>=1000 else str(int(y))))
    ax0.legend(fontsize=10, framealpha=0.8)

    if has_vol:
        ax1 = axes[1]
        ax1.bar(strikes-width*0.5, call_vol, width=width, color=BLUE,   alpha=0.85, label='Call Volume')
        ax1.bar(strikes+width*0.5, put_vol,  width=width, color=ORANGE, alpha=0.85, label='Put Volume')
        ax1.axvline(underlying, color=AMBER, lw=2, ls=':')
        ax1.set_xlabel('Strike Price ($)', fontsize=11)
        ax1.set_ylabel('Volume', fontsize=11)
        ax1.set_title('Volume by Strike (Today)', fontsize=12, fontweight='bold')
        ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'${x:.0f}'))
        ax1.legend(fontsize=10, framealpha=0.8)

    fig.tight_layout()
    save(fig, output_path)
    return {'max_pain': mp, 'put_call_ratio': round(pcr,3)}


def chart_theta_decay(params, output_path):
    K    = params['strike']
    S    = params.get('underlying', K)
    iv   = params.get('iv', 0.25)
    r    = params.get('r', 0.05)
    dmax = params.get('dte_max', 60)
    opt  = params.get('option_type','call')

    dtes   = np.arange(dmax, -1, -1)
    vals   = np.array([bs_price(S,K,max(d,0.001)/365,r,iv,opt) for d in dtes])
    thetas = np.array([bs_greeks(S,K,max(d,0.001)/365,r,iv,opt)['theta'] for d in dtes])
    intrin = max(S-K,0) if opt=='call' else max(K-S,0)

    fig, (ax1, ax2) = plt.subplots(2,1,figsize=(11,8), sharex=True)

    # Value decay
    ax1.plot(dtes, vals, color=GREEN, lw=2.5, label='Option Value')
    ax1.fill_between(dtes, vals, intrin, alpha=0.20, color=GREEN, label=f'Extrinsic (time) value')
    ax1.axhline(intrin, color=AMBER, lw=1.5, ls='--', label=f'Intrinsic: {intrin:.2f}')
    ax1.axvspan(0, 21, alpha=0.10, color=RED)
    ax1.annotate('⚠ Gamma Risk Zone\n(0–21 DTE)', xy=(10, vals.max()*0.85),
                 color=RED, fontsize=9, ha='center')
    ax1.set_ylabel('Option Value ($)', fontsize=11)
    ax1.set_title(f'Theta Decay — {opt.capitalize()} Strike {K} | IV {iv*100:.0f}pct | Underlying {S}',
                  fontsize=13, fontweight='bold', pad=12)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y,_: f'${y:.2f}'))
    ax1.legend(fontsize=9, framealpha=0.8)

    # Theta per day
    ax2.plot(dtes, thetas, color=RED, lw=2.5, label='Daily Theta (per day)')
    ax2.fill_between(dtes, thetas, 0, alpha=0.18, color=RED)
    ax2.axvspan(0, 21, alpha=0.10, color=RED)
    ax2.set_xlabel('Days to Expiration →', fontsize=11)
    ax2.set_ylabel('Theta ($ per day)', fontsize=11)
    ax2.set_title('Daily Time Decay (Theta)', fontsize=12, fontweight='bold')
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y,_: f'${y:.3f}'))
    ax2.invert_xaxis()
    ax2.legend(fontsize=9, framealpha=0.8)

    fig.tight_layout()
    save(fig, output_path)
    return {'initial_value': float(vals[0]), 'extrinsic': float(vals[0]-intrin)}


def chart_iv_history(params, output_path):
    dates  = params['dates']
    raw_iv = params['iv']
    raw_rv = params.get('rv', None)
    ticker = params.get('ticker','Underlying')

    iv_pct = [v*100 if v<5 else v for v in raw_iv]
    rv_pct = [v*100 if v and v<5 else (v or None) for v in raw_rv] if raw_rv else None

    iv_max = max(iv_pct)
    iv_min = min(iv_pct)
    iv_cur = iv_pct[-1]
    ivr    = round((iv_cur-iv_min)/(iv_max-iv_min)*100, 1) if iv_max!=iv_min else 50.0
    iv_avg = sum(iv_pct)/len(iv_pct)

    fig, ax = plt.subplots(figsize=(12,5.5))

    xs = range(len(dates))

    ax.plot(xs, iv_pct, color=BLUE, lw=2.5, marker='o', ms=4, label='Implied Volatility (IV)')
    ax.fill_between(xs, iv_pct, iv_avg, where=[v>iv_avg for v in iv_pct],
                    alpha=0.15, color=RED, label='Above avg IV (expensive)')
    ax.fill_between(xs, iv_pct, iv_avg, where=[v<=iv_avg for v in iv_pct],
                    alpha=0.15, color=GREEN, label='Below avg IV (cheap)')

    if rv_pct:
        ax.plot(xs, rv_pct, color=ORANGE, lw=2, ls='--', marker='s', ms=4,
                label='Realized Volatility (RV)')

    ax.axhline(iv_avg, color=GRID, lw=1, ls=':', label=f'52w Avg: {iv_avg:.1f}%')

    # IV Rank badge
    ivr_col = RED if ivr>70 else AMBER if ivr>40 else GREEN
    signal  = 'SELL PREMIUM' if ivr>70 else 'BUY OPTIONS' if ivr<30 else 'NEUTRAL'
    ax.annotate(f'IVR: {ivr:.0f}  →  {signal}',
                xy=(0.98,0.97), xycoords='axes fraction', ha='right', va='top',
                color=ivr_col, fontsize=12, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.4', facecolor=PANEL, edgecolor=ivr_col, lw=1.5))
    ax.annotate(f'Current IV: {iv_cur:.1f}%  |  52w High: {iv_max:.1f}%  |  52w Low: {iv_min:.1f}%',
                xy=(0.02,0.04), xycoords='axes fraction', ha='left', va='bottom',
                color=TEXT, fontsize=9)

    ax.set_xticks(list(xs))
    ax.set_xticklabels(dates, rotation=30, ha='right', fontsize=9)
    ax.set_ylabel('Implied Volatility (%)', fontsize=11)
    ax.set_title(f'IV History — {ticker}', fontsize=14, fontweight='bold', pad=12)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y,_: f'{y:.1f}%'))
    ax.legend(fontsize=9, framealpha=0.8)
    fig.tight_layout()
    save(fig, output_path)
    return {'iv_rank': ivr, 'current_iv': iv_cur, 'iv_avg': iv_avg}


def chart_multi_pnl(params, output_path):
    """Compare P&L of multiple strategies side by side."""
    strategies = params['strategies']
    underlying = params.get('underlying', 500)

    colors = [BLUE, GREEN, AMBER, PURPLE, ORANGE, RED]
    all_strikes = []
    for s in strategies:
        if 'short_put' in s: all_strikes += [s.get('short_put',0),s.get('long_put',0)]
        if 'short_call' in s: all_strikes += [s.get('short_call',0),s.get('long_call',0)]
        if 'strike' in s: all_strikes.append(s['strike'])
    all_strikes = [k for k in all_strikes if k>0]

    spread = max(max(all_strikes or [underlying]) - min(all_strikes or [underlying]),
                 underlying*0.15) * 1.6
    prices = np.linspace(underlying-spread, underlying+spread, 400)

    fig, ax = plt.subplots(figsize=(12,6.5))
    ax.axhline(0, color=GRID, lw=1.2, ls='--')
    ax.axvline(underlying, color=AMBER, lw=1.8, ls=':', label=f'Current price: {underlying}', zorder=6)

    for i, strat in enumerate(strategies):
        strat_params = {**strat, 'underlying': underlying}
        legs, credit = build_legs(strat_params)
        pnl = np.array([sum(leg_pnl(l,p) for l in legs) for p in prices])
        color = colors[i % len(colors)]
        name  = strat.get('name', f'Strategy {i+1}')
        ax.plot(prices, pnl, color=color, lw=2.5, label=f'{name} (credit ${credit:.2f})')

    ax.set_xlabel('Stock Price at Expiration ($)', fontsize=12)
    ax.set_ylabel('Profit / Loss ($)', fontsize=12)
    ax.set_title('Strategy Comparison — P&L at Expiration', fontsize=14, fontweight='bold', pad=12)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'${x:.0f}'))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y,_: f'${y:,.0f}'))
    ax.legend(fontsize=10, framealpha=0.8, loc='upper left')
    fig.tight_layout()
    save(fig, output_path)
    return {'output': output_path}


# ── CLI ────────────────────────────────────────────────────────────────────────

CHART_MAP = {
    'pnl':        chart_pnl,
    'iv_smile':   chart_iv_smile,
    'greeks':     chart_greeks,
    'oi_heatmap': chart_oi_heatmap,
    'theta_decay': chart_theta_decay,
    'iv_history': chart_iv_history,
    'multi_pnl':  chart_multi_pnl,
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Options Chart Generator')
    parser.add_argument('--chart',  required=True, choices=list(CHART_MAP.keys()))
    parser.add_argument('--params', required=True, help='JSON params string')
    parser.add_argument('--output', default=None,  help='Output PNG path')
    args = parser.parse_args()

    params = json.loads(args.params)
    output = args.output or f'/sessions/peaceful-funny-dijkstra/mnt/outputs/{args.chart}_chart.png'

    result = CHART_MAP[args.chart](params, output)
