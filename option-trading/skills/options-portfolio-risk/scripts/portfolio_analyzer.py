"""
Portfolio Risk Analyzer
========================
Generates aggregate Greeks, beta-weighted delta, and risk charts for an options portfolio.

Usage:
  python portfolio_analyzer.py \
    --positions '[{"ticker":"SPY","type":"put","strike":480,"dte":30,"qty":-10,"delta":-0.25,"theta":0.08,"vega":0.15,"underlying":505,"iv":0.18,"beta":1.0},...]' \
    --spy-price 505 \
    --account-size 100000 \
    --output /path/to/report.png
"""
import json, argparse, math, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import matplotlib.ticker as mticker
import numpy as np

BG=    '#111827'; PANEL='#1f2937'; TEXT='#e0e0e0'; GRID='#374151'
GREEN= '#00c853'; RED=  '#ef5350'; BLUE='#00bcd4'; AMBER='#FFC107'; PURPLE='#ab47bc'

plt.rcParams.update({'figure.facecolor':BG,'axes.facecolor':BG,'axes.edgecolor':GRID,
    'axes.labelcolor':TEXT,'axes.titlecolor':TEXT,'axes.grid':True,'grid.color':GRID,
    'grid.linewidth':0.6,'xtick.color':TEXT,'ytick.color':TEXT,'text.color':TEXT,
    'legend.facecolor':PANEL,'legend.edgecolor':GRID,'figure.dpi':140,'text.usetex':False})

DEFAULT_BETAS = {'SPY':1.0,'QQQ':1.1,'IWM':1.05,'GLD':0.05,'TLT':-0.25,
    'AAPL':1.20,'MSFT':1.05,'NVDA':1.70,'TSLA':1.85,'AMZN':1.15,
    'GOOGL':1.10,'META':1.25,'AMD':1.60,'NFLX':1.30,'UBER':1.40}

def analyze(positions, spy_price, account_size):
    total = {'delta':0,'gamma':0,'theta':0,'vega':0,'bw_delta':0,'positions':[]}
    for p in positions:
        qty = p['qty']; mult = 100
        pdelta = p.get('delta',0) * qty * mult
        pgamma = p.get('gamma',0) * qty * mult
        ptheta = p.get('theta',0) * qty * mult
        pvega  = p.get('vega',0)  * qty * mult
        beta   = p.get('beta', DEFAULT_BETAS.get(p['ticker'].upper(), 1.0))
        bw_delta = pdelta * (p.get('underlying', spy_price) / spy_price) * beta
        total['delta']    += pdelta
        total['gamma']    += pgamma
        total['theta']    += ptheta
        total['vega']     += pvega
        total['bw_delta'] += bw_delta
        total['positions'].append({**p,'pdelta':pdelta,'pgamma':pgamma,'ptheta':ptheta,'pvega':pvega,'bw_delta':bw_delta})
    return total

def save(fig, path):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    fig.savefig(path, bbox_inches='tight', facecolor=BG, dpi=140)
    plt.close(fig)

def generate_report(positions, spy_price, account_size, output_path):
    agg = analyze(positions, spy_price, account_size)
    n   = len(positions)

    fig = plt.figure(figsize=(15, 10))
    gs  = GridSpec(2, 3, figure=fig, hspace=0.55, wspace=0.40)

    # ── 1: Greeks bar chart ──────────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    greeks = ['Delta','Gamma\n(×1000)','Theta\n($/day)','Vega\n(per 1%IV)']
    vals   = [agg['delta'], agg['gamma']*1000, agg['theta'], agg['vega']]
    colors = [GREEN if v>=0 else RED for v in vals]
    bars   = ax1.bar(greeks, vals, color=colors, alpha=0.85, edgecolor=GRID, linewidth=0.8)
    ax1.axhline(0, color=GRID, lw=1.2, ls='--')
    for bar, v in zip(bars, vals):
        ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+(max(vals)*0.02),
                 f'{v:+.1f}', ha='center', va='bottom', fontsize=9, color=TEXT)
    ax1.set_title('Aggregate Greeks', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Value', fontsize=10)

    # ── 2: Beta-weighted delta gauge ─────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    bwd  = agg['bw_delta']
    max_bwd = max(abs(bwd)*1.5, 500)
    ax2.barh(['Beta-Weighted\nDelta (vs SPY)'], [bwd],
             color=GREEN if bwd>=0 else RED, alpha=0.85, height=0.4)
    ax2.axvline(0, color=GRID, lw=1.5, ls='--')
    ax2.set_xlim(-max_bwd, max_bwd)
    ax2.set_title('Beta-Weighted Delta', fontsize=12, fontweight='bold')
    direction = 'BULLISH' if bwd > 200 else 'BEARISH' if bwd < -200 else 'NEUTRAL'
    dir_color = GREEN if bwd > 200 else RED if bwd < -200 else AMBER
    ax2.annotate(f'{bwd:+.0f}\n({direction})',
                 xy=(0.5, 0.25), xycoords='axes fraction', ha='center',
                 fontsize=13, fontweight='bold', color=dir_color)
    spy_equiv = bwd / 100
    ax2.annotate(f'Like {spy_equiv:+.1f} SPY shares',
                 xy=(0.5, 0.10), xycoords='axes fraction', ha='center',
                 fontsize=10, color=TEXT)

    # ── 3: Risk at price (P&L vs SPY move) ───────────────────────────────────
    ax3 = fig.add_subplot(gs[0, 2])
    moves = np.linspace(-0.15, 0.15, 31)
    pnl   = [agg['bw_delta'] * m * spy_price for m in moves]
    colors_pnl = [GREEN if v>=0 else RED for v in pnl]
    ax3.bar(moves*100, pnl, color=colors_pnl, alpha=0.80, width=0.8)
    ax3.axhline(0, color=GRID, lw=1.2, ls='--')
    ax3.axvline(0, color=AMBER, lw=1.5, ls=':', label='No change')
    ax3.set_xlabel('SPY Move (%)', fontsize=10)
    ax3.set_ylabel('Estimated P&L', fontsize=10)
    ax3.set_title('Portfolio P&L vs SPY Move\n(delta approximation)', fontsize=11, fontweight='bold')
    ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y,_: f'${y:,.0f}'))

    # ── 4: Position breakdown table ──────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 0:2])
    ax4.axis('off')
    rows = []
    for p in agg['positions']:
        side = 'Short' if p['qty'] < 0 else 'Long'
        rows.append([
            f"{p['ticker']}", f"{side} {abs(p['qty'])}× {p['type'].capitalize()} {p['strike']}",
            f"{p.get('dte','-')}d", f"{p['pdelta']:+.0f}",
            f"{p['ptheta']:+.2f}", f"{p['pvega']:+.2f}", f"{p['bw_delta']:+.0f}"
        ])
    col_labels = ['Ticker','Position','DTE','Delta','Theta/day','Vega/1%IV','BW-Delta']
    tbl = ax4.table(cellText=rows, colLabels=col_labels, loc='center', cellLoc='center')
    tbl.auto_set_font_size(False); tbl.set_fontsize(9)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_facecolor('#1f2937' if r==0 else BG)
        cell.set_edgecolor(GRID)
        cell.set_text_props(color=AMBER if r==0 else TEXT)
    ax4.set_title('Position Breakdown', fontsize=12, fontweight='bold', pad=20)

    # ── 5: Summary stats + alerts ─────────────────────────────────────────────
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.axis('off')
    daily_theta_pct = abs(agg['theta']) / account_size * 100
    alerts = []
    if abs(agg['bw_delta']) > account_size * 0.01:
        alerts.append(f"! Large directional exposure: {agg['bw_delta']:+.0f} BW-delta")
    if agg['gamma'] < -50:
        alerts.append("! Negative gamma — risk in big moves")
    if agg['vega'] < -5000:
        alerts.append("! High short vega — vol spike risk")
    if daily_theta_pct > 0.5:
        alerts.append("! Very high theta — over-exposed?")
    if not alerts:
        alerts = ["No major risk alerts"]

    summary = (
        f"Portfolio Risk Summary\n"
        f"{'─'*28}\n"
        f"Positions:    {n}\n"
        f"Net Delta:    {agg['delta']:+.0f}\n"
        f"BW Delta:     {agg['bw_delta']:+.0f} (SPY equiv)\n"
        f"Daily Theta:  ${agg['theta']:+.2f}/day\n"
        f"Net Vega:     ${agg['vega']:+.2f}/1% IV\n"
        f"Theta % Acct: {daily_theta_pct:.3f}%/day\n"
        f"{'─'*28}\n"
        f"ALERTS:\n" + "\n".join(alerts)
    )
    ax5.text(0.05, 0.95, summary, transform=ax5.transAxes,
             fontsize=9, va='top', ha='left', color=TEXT,
             fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor=PANEL, edgecolor=AMBER, lw=1.5))

    fig.suptitle('Portfolio Risk Dashboard', fontsize=16, fontweight='bold', y=1.01)
    save(fig, output_path)
    return {'total_delta': agg['delta'], 'bw_delta': agg['bw_delta'],
            'daily_theta': agg['theta'], 'total_vega': agg['vega'],
            'output': output_path}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--positions', required=True)
    parser.add_argument('--spy-price', type=float, default=500)
    parser.add_argument('--account-size', type=float, default=100000)
    parser.add_argument('--output', default='/sessions/peaceful-funny-dijkstra/mnt/outputs/portfolio_risk.png')
    args = parser.parse_args()
    positions = json.loads(args.positions)
    result = generate_report(positions, args.spy_price, args.account_size, args.output)
    print(json.dumps(result))
