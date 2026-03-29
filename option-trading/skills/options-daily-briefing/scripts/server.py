"""
Options Daily Briefing  —  Live Web Server
============================================
Run this once, then open http://localhost:8080 in your browser.

Features:
  • Dashboard auto-refreshes every 60 seconds (full re-scan of all tickers)
  • Open positions update every 10 seconds (live price feed if connected)
  • Click "Invest" → modal → confirm → order placed via Alpaca
  • Portfolio panel shows total P&L, all open/closed trades
  • All trade data stored PERMANENTLY in ~/.options_briefing/portfolio.db

Usage:
  python server.py                   # demo mode, port 8080
  python server.py --port 3000       # custom port
  python server.py --live            # use live market data (needs Alpaca keys)
  python server.py --scan-every 120  # re-scan every 120 seconds

Setup Alpaca (for live data + real orders):
  export ALPACA_API_KEY="your_key"
  export ALPACA_SECRET_KEY="your_secret"
  export ALPACA_PAPER=true           # paper trading (safe default)
"""

import sys, os, json, time, threading, argparse, traceback
from datetime import datetime
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from screener   import scan_all, TIMEFRAMES
from universe   import generate_universe_demo
from portfolio  import Portfolio
from broker     import Broker
from analysis_engine import detect_regime
from table_renderer  import render_live_dashboard

# ── Flask ──────────────────────────────────────────────────────────────────────
try:
    from flask import Flask, Response, request, jsonify, stream_with_context
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

app       = Flask(__name__) if HAS_FLASK else None
portfolio = Portfolio()
broker    = Broker()

# ── Shared state (thread-safe via a lock) ─────────────────────────────────────
_lock       = threading.Lock()
_scan_cache = {'data': {}, 'vix': 18.0, 'date': '', 'regime_counts': {},
               'universe_size': 0, 'last_scan': 0}
_sse_clients: list = []    # active SSE connections

# ── Background: Market Scanner ────────────────────────────────────────────────

def _run_scan(use_demo: bool):
    """One full market scan. Updates _scan_cache and broadcasts to SSE clients."""
    global _scan_cache
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning market...", flush=True)

        if use_demo or not broker.connected:
            universe = generate_universe_demo()
            vix = 18.0
        else:
            from data_fetcher import fetch_all
            from universe import TRADEABLE
            tickers  = list(TRADEABLE.keys())
            raw      = fetch_all(tickers)
            universe = raw.get('tickers', {})
            vix      = raw.get('vix', broker.get_vix() or 18.0)

        # Regime counts
        regime_counts = {}
        for td in universe.values():
            closes = td.get('closes', [])
            if len(closes) < 30:
                continue
            try:
                r = detect_regime(closes, vix)
                t = r.get('trend', 'sideways').capitalize()
                regime_counts[t] = regime_counts.get(t, 0) + 1
            except Exception:
                pass

        ranked = scan_all(universe, vix=vix, top_n=20)
        today  = datetime.now().strftime('%b %d, %Y')

        with _lock:
            _scan_cache.update({
                'data':           ranked,
                'vix':            vix,
                'date':           today,
                'regime_counts':  regime_counts,
                'universe_size':  len(universe),
                'last_scan':      time.time(),
            })

        # Broadcast to all connected SSE clients
        _broadcast({'type': 'scan', 'ts': int(time.time()),
                    'vix': vix, 'date': today,
                    'regime_counts': regime_counts,
                    'universe_size': len(universe),
                    'picks': {tf: len(ranked.get(tf, [])) for tf in TIMEFRAMES}})

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Scan complete. "
              f"Picks: " + " | ".join(f"{tf}: {len(ranked.get(tf,[]))}"
                                       for tf in TIMEFRAMES), flush=True)
    except Exception as e:
        print(f"[Scanner] ERROR: {e}", flush=True)
        traceback.print_exc()


def _scanner_thread(use_demo: bool, interval: int):
    """Background thread: re-scan every `interval` seconds."""
    _run_scan(use_demo)   # first scan immediately
    while True:
        time.sleep(interval)
        _run_scan(use_demo)


def _position_updater_thread():
    """Background thread: refresh open position prices every 10 seconds."""
    while True:
        time.sleep(10)
        try:
            positions = portfolio.get_open_positions()
            if not positions:
                continue

            if broker.connected:
                updates = broker.refresh_position_prices(positions)
                if updates:
                    portfolio.update_prices_bulk(updates)

            # Check for auto-exits (target hit / stop hit)
            for pos in positions:
                cp = pos.get('current_price') or pos['entry_price']
                tp = pos['target_price']
                sp = pos['stop_price']
                if cp >= tp:
                    portfolio.close_trade(pos['id'], cp, 'target_hit')
                    print(f"✓ AUTO-SELL {pos['ticker']}: Target hit! "
                          f"${pos['entry_price']} → ${cp}", flush=True)
                    _broadcast({'type': 'position_closed',
                                'id': pos['id'], 'reason': 'target_hit',
                                'exit_price': cp})
                elif cp <= sp:
                    portfolio.close_trade(pos['id'], cp, 'stop_hit')
                    print(f"✗ AUTO-SELL {pos['ticker']}: Stop hit. "
                          f"${pos['entry_price']} → ${cp}", flush=True)
                    _broadcast({'type': 'position_closed',
                                'id': pos['id'], 'reason': 'stop_hit',
                                'exit_price': cp})

            # Broadcast updated portfolio
            summary   = portfolio.get_summary()
            positions = portfolio.get_open_positions()
            _broadcast({'type': 'portfolio',
                        'summary':   summary,
                        'positions': positions})
        except Exception as e:
            print(f"[PositionUpdater] {e}", flush=True)


# ── SSE broadcast ──────────────────────────────────────────────────────────────

def _broadcast(data: dict):
    msg = f"data: {json.dumps(data)}\n\n"
    dead = []
    for q in _sse_clients:
        try:
            q.put(msg)
        except Exception:
            dead.append(q)
    for d in dead:
        _sse_clients.remove(d)


# ── Flask routes ───────────────────────────────────────────────────────────────

if HAS_FLASK:
    @app.route('/')
    def index():
        """Serve the live HTML dashboard."""
        with _lock:
            cache = dict(_scan_cache)
        html = render_live_dashboard(
            ranked         = cache.get('data', {}),
            date_str       = cache.get('date', datetime.now().strftime('%b %d, %Y')),
            vix            = cache.get('vix', 18.0),
            regime_counts  = cache.get('regime_counts', {}),
            portfolio_summary = portfolio.get_summary(),
            open_positions    = portfolio.get_open_positions(),
            broker_mode       = broker.mode,
            broker_connected  = broker.connected,
        )
        return html

    @app.route('/api/scan')
    def api_scan():
        """Return latest scan results as JSON."""
        with _lock:
            return jsonify({
                'vix':           _scan_cache['vix'],
                'date':          _scan_cache['date'],
                'last_scan':     _scan_cache['last_scan'],
                'regime_counts': _scan_cache['regime_counts'],
                'picks':         {tf: _scan_cache['data'].get(tf, [])
                                  for tf in TIMEFRAMES},
            })

    @app.route('/api/portfolio')
    def api_portfolio():
        """Return portfolio summary + positions."""
        return jsonify({
            'summary':   portfolio.get_summary(),
            'positions': portfolio.get_open_positions(),
            'history':   portfolio.get_closed_trades(50),
        })

    @app.route('/api/account')
    def api_account():
        return jsonify(broker.get_account())

    @app.route('/api/order', methods=['POST'])
    def api_order():
        """Place a new options order."""
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data'}), 400

        # Validate required fields
        required = ['ticker','option_type','strike','expiry','dte',
                    'contracts','entry_price','target_price','stop_price']
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({'error': f'Missing fields: {missing}'}), 400

        # Safety: never place live order without explicit confirmation
        if not broker.cfg['paper'] and not data.get('confirmed_live', False):
            return jsonify({'error': 'Live trading requires confirmed_live=true'}), 403

        # Place order via broker
        order_result = broker.place_option_order(data)

        if order_result['status'] in ('submitted', 'pending_new', 'demo_placed'):
            # Record in portfolio
            trade_id = portfolio.record_trade({
                **data,
                'alpaca_order_id': order_result.get('order_id'),
                'mode':            'paper' if broker.cfg['paper'] else 'live',
                'stock_price':     data.get('stock_price'),
                'iv':              data.get('iv'),
                'delta':           data.get('delta'),
                'score':           data.get('score'),
            })
            order_result['trade_id'] = trade_id
            # Broadcast updated portfolio
            _broadcast({'type': 'portfolio',
                        'summary':   portfolio.get_summary(),
                        'positions': portfolio.get_open_positions()})
            return jsonify({'success': True, **order_result})
        else:
            return jsonify({'success': False, **order_result}), 500

    @app.route('/api/close/<int:trade_id>', methods=['POST'])
    def api_close(trade_id: int):
        """Manually close an open position."""
        data       = request.get_json() or {}
        exit_price = data.get('exit_price', 0)
        reason     = data.get('reason', 'manual')

        positions = portfolio.get_open_positions()
        pos = next((p for p in positions if p['id'] == trade_id), None)
        if not pos:
            return jsonify({'error': 'Position not found'}), 404

        # Close via broker if connected
        broker.close_position(
            alpaca_order_id=pos.get('alpaca_order_id'),
            ticker=pos['ticker'])

        # Use current price if not provided
        if not exit_price:
            exit_price = pos.get('current_price') or pos['entry_price']

        portfolio.close_trade(trade_id, exit_price, reason)
        _broadcast({'type': 'position_closed',
                    'id': trade_id, 'reason': reason, 'exit_price': exit_price})
        _broadcast({'type': 'portfolio',
                    'summary':   portfolio.get_summary(),
                    'positions': portfolio.get_open_positions()})
        return jsonify({'success': True, 'exit_price': exit_price})

    @app.route('/api/stream')
    def api_stream():
        """Server-Sent Events endpoint for live updates."""
        from queue import Queue
        q = Queue()
        _sse_clients.append(q)

        # Send initial portfolio state immediately
        init_data = json.dumps({
            'type':      'init',
            'portfolio': portfolio.get_summary(),
            'positions': portfolio.get_open_positions(),
            'broker':    broker.mode,
            'connected': broker.connected,
        })

        def generate():
            yield f"data: {init_data}\n\n"
            while True:
                try:
                    msg = q.get(timeout=30)
                    yield msg
                except Exception:
                    yield ": keepalive\n\n"   # SSE heartbeat

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control':  'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection':     'keep-alive',
            })

    @app.route('/api/export')
    def api_export():
        """Export portfolio to JSON."""
        path = portfolio.export_to_json()
        return jsonify({'success': True, 'path': path})


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    if not HAS_FLASK:
        print("ERROR: Flask not installed. Run:  pip install flask")
        print("Then re-run:  python server.py")
        sys.exit(1)

    parser = argparse.ArgumentParser(description='Options Daily Briefing Live Server')
    parser.add_argument('--port',       type=int,  default=8080)
    parser.add_argument('--live',       action='store_true', help='Use live market data')
    parser.add_argument('--scan-every', type=int,  default=60,
                        help='Re-scan interval in seconds (default: 60)')
    parser.add_argument('--demo',       action='store_true', help='Force demo mode')
    args = parser.parse_args()

    use_demo = args.demo or (not args.live and not broker.connected)

    print(f"\n{'='*60}")
    print(f"  Options Daily Briefing — Live Server")
    print(f"  Mode:     {'DEMO (synthetic data)' if use_demo else broker.mode}")
    print(f"  Broker:   {'Connected to Alpaca' if broker.connected else 'Not connected (demo)'}")
    print(f"  Portfolio: {portfolio.db_path}")
    print(f"  Scan every: {args.scan_every}s")
    print(f"{'='*60}")
    print(f"\n  Open in browser: http://localhost:{args.port}")
    print(f"  Press Ctrl+C to stop\n")

    # Start background threads
    t1 = threading.Thread(target=_scanner_thread,
                          args=(use_demo, args.scan_every), daemon=True)
    t2 = threading.Thread(target=_position_updater_thread, daemon=True)
    t1.start()
    t2.start()

    app.run(host='0.0.0.0', port=args.port, debug=False, threaded=True)


if __name__ == '__main__':
    main()
