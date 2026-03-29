"""
Options Daily Briefing  —  Main Runner
=========================================
Wake up, run this, open the HTML.

Pipeline:
  1. Load universe data (demo OR live JSON from data_fetcher.py)
  2. Scan every ticker × 3 timeframes
  3. Score and rank all candidates
  4. Render 3 compact ranked tables (short / mid / long)
  5. Save self-contained HTML

Usage:
  # Demo mode — no data needed, scans 80+ synthetic tickers:
  python daily_briefing.py --demo

  # Live mode — real market data (run data_fetcher.py first):
  python daily_briefing.py --input market_data.json

  # Custom output:
  python daily_briefing.py --demo --output ~/Desktop/briefing.html

  # How many top picks per table:
  python daily_briefing.py --demo --top 15
"""

import sys, os, json, argparse
from datetime import date, timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from screener       import scan_all, TIMEFRAMES
from table_renderer import render_tables

# ─────────────────────────────────────────────────────────────────────────────

def load_universe(input_path, use_demo):
    if use_demo or not input_path:
        print("DEMO mode — generating synthetic data for 80+ tickers...", flush=True)
        from universe import generate_universe_demo
        return generate_universe_demo(), None
    else:
        print(f"Loading live data: {input_path}", flush=True)
        with open(input_path) as f:
            raw = json.load(f)
        vix = raw.get('vix', 18.0)
        return raw.get('tickers', {}), vix

def main():
    parser = argparse.ArgumentParser(description='Options Daily Briefing')
    parser.add_argument('--demo',   action='store_true', help='Use demo data')
    parser.add_argument('--input',  default=None,        help='Path to market_data.json')
    parser.add_argument('--output', default=None,        help='Output HTML path')
    parser.add_argument('--top',    type=int, default=20,help='Picks per timeframe table')
    parser.add_argument('--vix',    type=float, default=None, help='Override VIX level')
    args = parser.parse_args()

    use_demo = args.demo or (args.input is None)

    # ── Load data ──────────────────────────────────────────────────────────
    universe, data_vix = load_universe(args.input, use_demo)
    vix = args.vix or data_vix or 18.0

    today_str = date.today().strftime('%b %d, %Y')

    # Default output path
    if not args.output:
        out_dir = os.path.join(os.path.dirname(_HERE), 'output')
        os.makedirs(out_dir, exist_ok=True)
        fname = f"briefing_{date.today().strftime('%Y%m%d')}.html"
        args.output = os.path.join(out_dir, fname)

    print(f"\n{'='*60}")
    print(f"  Options Daily Briefing  —  {today_str}")
    print(f"  VIX: {vix:.1f}   Universe: {len(universe)} tickers")
    print(f"  Mode: {'DEMO' if use_demo else 'LIVE'}")
    print(f"  Output: {args.output}")
    print(f"{'='*60}\n")

    # ── Scan all tickers ────────────────────────────────────────────────────
    print("Scanning universe...", flush=True)
    ranked = scan_all(universe, vix=vix, top_n=args.top)

    # ── Compute regime summary across universe ──────────────────────────────
    regime_counts = {}
    from analysis_engine import detect_regime
    for td in universe.values():
        closes = td.get('closes', [])
        if len(closes) < 30:
            continue
        try:
            regime = detect_regime(closes, vix)
            t = regime.get('trend', 'sideways').capitalize()
            regime_counts[t] = regime_counts.get(t, 0) + 1
        except Exception:
            pass

    # ── Print summary ───────────────────────────────────────────────────────
    print()
    for tf, tf_info in TIMEFRAMES.items():
        picks = ranked.get(tf, [])
        print(f"  {tf_info['label']:30s} → {len(picks)} picks")
        for i, c in enumerate(picks[:5]):
            print(f"    {i+1}. {c['ticker']:6s} {c['option_type']:4s} "
                  f"${c['strike']:7.2f}  entry ${c['entry']:.2f}  "
                  f"score {c['score']:.0f}  P(hit) {c['p_touch']:.0f}%")
        print()

    # ── Render HTML ─────────────────────────────────────────────────────────
    print("Rendering dashboard...", flush=True)
    html = render_tables(ranked, today_str, vix, regime_counts)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)

    size_kb = os.path.getsize(args.output) // 1024
    print(f"\n{'='*60}")
    print(f"  ✓  Saved: {args.output}  ({size_kb} KB)")
    print(f"     Open in your browser to view the briefing.")
    print(f"{'='*60}\n")

    return args.output

if __name__ == '__main__':
    main()
