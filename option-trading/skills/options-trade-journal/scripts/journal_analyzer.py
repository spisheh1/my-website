"""
Trade Journal Analyzer & Performance Charts
=============================================
Generates performance analytics charts from a list of trades.

Usage:
  python journal_analyzer.py \
    --trades '[{"id":1,"date":"2025-01-10","ticker":"SPY","strategy":"Iron Condor",
               "pnl":175,"max_profit":350,"max_loss":650,"ivr_entry":72,"dte_entry":38,"win":true},...]' \
    --output /path/to/report.png
"""
import json, argparse, os, math
from datetime import datetime
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.ticker as mticker
import numpy as np

BG=    '#111827'; PANEL='#1f2937'; TEXT='#e0e0e0'; GRID='#374151'
GREEN= '#00c853'; RED=  '#ef5350'; BLUE='#00bcd4'; AMBER='#FFC107'; PURPLE='#ab47bc'

plt.rcParams.update({'figure.facecolor':BG,'axes.facecolor':BG,'axes.edgecolor':GRID,
    'axes.labelcolor':TEXT,'axes.titlecolor':TEXT,'axes.grid':True,'grid.color':GRID,
    'grid.linewidth':0.6,'xtick.color':TEXT,'ytick.color':TEXT,'text.color':TEXT,
    'legend.facecolor':PANEL,'legend.edgecolor':GRID,'figure.dpi':140,'text.usetex':False})

def calc_stats(trades):
    if not trades: return {}
    pnls   = [t['pnl'] for t in trades]
    wins   = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = len(wins)/len(pnls)*100 if pnls else 0
    avg_win  = sum(wins)/len(wins) if wins else 0
    avg_loss = abs(sum(losses)/len(losses)) if losses else 0
    gross_profit = sum(wins)
    gross_loss   = abs(sum(losses))
    profit_factor = gross_profit/gross_loss if gross_loss > 0 else float('inf')
    expectancy = (win_rate/100 * avg_win) - ((1-win_rate/100) * avg_loss)
    # Equity curve
    equity = list(np.cumsum(pnls))
    max_eq = equity[0] if equity else 0
    max_dd = 0
    for e in equity:
        max_eq = max(max_eq, e)
        max_dd = max(max_dd, max_eq - e)
    return {
        'total_trades': len(trades),
        'wins': len(wins), 'losses': len(losses),
        'win_rate': round(win_rate,1),
        'avg_win': round(avg_win,2),
        'avg_loss': round(avg_loss,2),
        'win_loss_ratio': round(avg_win/avg_loss,2) if avg_loss>0 else 0,
        'profit_factor': round(profit_factor,2),
        'expectancy': round(expectancy,2),
        'total_pnl': round(sum(pnls),2),
        'max_drawdown': round(max_dd,2),
        'equity': equity
    }

def save(fig, path):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    fig.savefig(path, bbox_inches='tight', facecolor=BG, dpi=140)
    plt.close(fig)

def generate_report(trades, output_path):
    stats = calc_stats(trades)
    pnls  = [t['pnl'] for t in trades]
    dates = [t.get('date',f'T{t.get("id",i+1)}') for i,t in enumerate(trades)]

    fig = plt.figure(figsize=(16, 10))
    gs  = GridSpec(2, 3, figure=fig, hspace=0.50, wspace=0.38)

    # ── 1: Equity Curve ───────────────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0:2])
    equity = stats['equity']
    xs = range(len(equity))
    color_line = GREEN if equity[-1] >= 0 else RED
    ax1.plot(xs, equity, color=color_line, lw=2.5, label='Cumulative P&L')
    ax1.fill_between(xs, equity, 0, where=[e>=0 for e in equity], alpha=0.15, color=GREEN)
    ax1.fill_between(xs, equity, 0, where=[e<0  for e in equity], alpha=0.15, color=RED)
    ax1.axhline(0, color=GRID, lw=1.2, ls='--')
    ax1.set_xticks(list(xs)[::max(1,len(xs)//10)])
    ax1.set_xticklabels([dates[i] for i in list(xs)[::max(1,len(xs)//10)]], rotation=30, ha='right', fontsize=8)
    ax1.set_ylabel('Cumulative P&L', fontsize=11)
    ax1.set_title('Equity Curve', fontsize=13, fontweight='bold')
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y,_: f'${y:,.0f}'))

    # ── 2: P&L Distribution ───────────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 2])
    wins_pnl  = [p for p in pnls if p > 0]
    loss_pnl  = [p for p in pnls if p <= 0]
    bins = np.linspace(min(pnls)-50, max(pnls)+50, 20)
    ax2.hist(wins_pnl, bins=bins, color=GREEN, alpha=0.75, label=f'Wins ({len(wins_pnl)})')
    ax2.hist(loss_pnl, bins=bins, color=RED,   alpha=0.75, label=f'Losses ({len(loss_pnl)})')
    ax2.axvline(0, color=GRID, lw=1.5, ls='--')
    ax2.axvline(stats['avg_win'],  color=GREEN, lw=1.5, ls=':', label=f'Avg win: ${stats["avg_win"]:,.0f}')
    ax2.axvline(-stats['avg_loss'], color=RED, lw=1.5, ls=':', label=f'Avg loss: -${stats["avg_loss"]:,.0f}')
    ax2.set_xlabel('P&L per Trade', fontsize=10)
    ax2.set_ylabel('Frequency', fontsize=10)
    ax2.set_title('P&L Distribution', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=8, framealpha=0.8)
    ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'${x:,.0f}'))

    # ── 3: Win Rate by Strategy ───────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    strat_stats = defaultdict(lambda: {'wins':0,'total':0,'pnl':0})
    for t in trades:
        s = t.get('strategy','Unknown')
        strat_stats[s]['total'] += 1
        strat_stats[s]['pnl']   += t['pnl']
        if t['pnl'] > 0: strat_stats[s]['wins'] += 1
    strats   = list(strat_stats.keys())
    wr_vals  = [strat_stats[s]['wins']/strat_stats[s]['total']*100 for s in strats]
    bar_cols = [GREEN if w>=55 else AMBER if w>=40 else RED for w in wr_vals]
    ax3.barh(strats, wr_vals, color=bar_cols, alpha=0.85, height=0.5)
    ax3.axvline(50, color=AMBER, lw=1.5, ls=':', label='50% line')
    ax3.set_xlabel('Win Rate (%)', fontsize=10)
    ax3.set_title('Win Rate by Strategy', fontsize=12, fontweight='bold')
    ax3.set_xlim(0, 100)
    for i, v in enumerate(wr_vals):
        ax3.text(v+1, i, f'{v:.0f}%', va='center', fontsize=9, color=TEXT)

    # ── 4: IVR Entry vs P&L scatter ──────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    ivr_data  = [(t.get('ivr_entry',50), t['pnl']) for t in trades if 'ivr_entry' in t]
    if ivr_data:
        ivrs, p_ivr = zip(*ivr_data)
        colors_sc = [GREEN if p>0 else RED for p in p_ivr]
        ax4.scatter(ivrs, p_ivr, c=colors_sc, alpha=0.75, s=60, edgecolors=GRID, lw=0.5)
        ax4.axhline(0, color=GRID, lw=1.2, ls='--')
        ax4.axvline(50, color=AMBER, lw=1.5, ls=':', label='IVR 50')
        # Trend line
        if len(ivrs) > 3:
            z = np.polyfit(ivrs, p_ivr, 1)
            p_fit = np.poly1d(z)
            xr = np.linspace(min(ivrs), max(ivrs), 50)
            ax4.plot(xr, p_fit(xr), color=BLUE, lw=2, ls='--', label='Trend')
        ax4.set_xlabel('IVR at Entry', fontsize=10)
        ax4.set_ylabel('Trade P&L', fontsize=10)
        ax4.set_title('IVR Entry vs P&L', fontsize=12, fontweight='bold')
        ax4.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y,_: f'${y:,.0f}'))
        ax4.legend(fontsize=8)

    # ── 5: Performance Stats Summary ─────────────────────────────────────────
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.axis('off')
    pf_color   = GREEN if stats['profit_factor'] >= 1.5 else AMBER if stats['profit_factor'] >= 1.0 else RED
    exp_color  = GREEN if stats['expectancy'] > 0 else RED
    wr_color   = GREEN if stats['win_rate'] >= 55 else AMBER if stats['win_rate'] >= 45 else RED

    summary_text = (
        f"PERFORMANCE SUMMARY\n"
        f"{'─'*24}\n"
        f"Total Trades:  {stats['total_trades']}\n"
        f"Win Rate:      {stats['win_rate']:.1f}%\n"
        f"Avg Win:       ${stats['avg_win']:,.0f}\n"
        f"Avg Loss:      -${stats['avg_loss']:,.0f}\n"
        f"W/L Ratio:     {stats['win_loss_ratio']:.2f}\n"
        f"Profit Factor: {stats['profit_factor']:.2f}\n"
        f"Expectancy:    ${stats['expectancy']:,.0f}/trade\n"
        f"Total P&L:     ${stats['total_pnl']:,.0f}\n"
        f"Max Drawdown:  -${stats['max_drawdown']:,.0f}\n"
        f"{'─'*24}\n"
        f"{'PROFITABLE' if stats['total_pnl']>0 else 'LOSING'} | "
        f"Edge: {'YES' if stats['expectancy']>0 else 'NO'}"
    )
    ax5.text(0.05, 0.95, summary_text, transform=ax5.transAxes,
             fontsize=9, va='top', ha='left', color=TEXT,
             fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor=PANEL,
                       edgecolor=GREEN if stats['total_pnl']>0 else RED, lw=2))

    fig.suptitle('Trade Journal Performance Report', fontsize=15, fontweight='bold', y=1.01)
    save(fig, output_path)
    return {**stats, 'output': output_path}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--trades', required=True)
    parser.add_argument('--output', default='/sessions/peaceful-funny-dijkstra/mnt/outputs/journal_report.png')
    args = parser.parse_args()
    trades = json.loads(args.trades)
    result = generate_report(trades, args.output)
    print(json.dumps({k:(float(v) if hasattr(v,'item') else v) for k,v in result.items() if k != 'equity'}))
