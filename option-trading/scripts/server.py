"""
Options Trading Dashboard — Fast Server
========================================
- Starts instantly, no waiting for scan
- Scan runs in background, pushed to browser via SSE when ready
- Live prices pushed via SSE every 2 seconds
- Top 10 re-ranked every 10 seconds as prices move
- Option bid/ask fetched from yfinance options chain

Run:  python server.py --demo
Open: http://localhost:8080
"""

import sys, os, json, time, threading, argparse, traceback, queue
import hashlib, hmac, secrets, smtplib, sqlite3
from datetime import datetime, date, timedelta
from email.mime.text import MIMEText
from concurrent.futures import ThreadPoolExecutor

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

try:
    from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context, session, redirect
except ImportError:
    print("ERROR: Flask not installed.  Run:  pip install flask"); sys.exit(1)

from pathlib   import Path
from screener  import scan_ticker, scan_all, TIMEFRAMES
from universe  import generate_universe_demo
from portfolio import Portfolio
from broker    import Broker

app    = Flask(__name__, static_folder=_HERE)
broker = Broker()

# ── Session / auth config ───────────────────────────────────────────────────────
app.secret_key = os.environ.get('FLASK_SECRET', 'options-trader-secret-change-in-prod-2024')
app.config['SESSION_COOKIE_PATH']     = '/'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# ── Per-user portfolio registry ────────────────────────────────────────────────
_portfolios: dict = {}   # { username: Portfolio }
_port_lock = threading.Lock()

def _data_dir() -> Path:
    d = Path(os.environ.get('TRADING_DATA_DIR', str(Path.home() / '.options_briefing')))
    d.mkdir(parents=True, exist_ok=True)
    return d

# ── User management ────────────────────────────────────────────────────────────

def _users_db_path() -> str:
    return str(_data_dir() / 'users.db')

def _init_users_db():
    """Create the users table if it doesn't exist."""
    with sqlite3.connect(_users_db_path()) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email       TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now')),
                is_active   INTEGER DEFAULT 1
            )""")
        conn.commit()

def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk   = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100_000)
    return f"{salt}:{dk.hex()}"

def _verify_password(stored: str, provided: str) -> bool:
    try:
        salt, dk = stored.split(':', 1)
        dk2 = hashlib.pbkdf2_hmac('sha256', provided.encode(), salt.encode(), 100_000)
        return hmac.compare_digest(dk.encode(), dk2.hex().encode())
    except Exception:
        return False

def _get_user(username: str):
    """Return user row or None."""
    with sqlite3.connect(_users_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM users WHERE username=? AND is_active=1",
            (username.lower().strip(),)
        ).fetchone()

def _create_user(username: str, password: str, email: str = '') -> bool:
    """Create user. Returns True on success, False if username taken."""
    try:
        with sqlite3.connect(_users_db_path()) as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, email) VALUES (?,?,?)",
                (username.lower().strip(), _hash_password(password), email.strip())
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def _ensure_default_users():
    """Seed sam, hojr, and bot users if they don't exist yet."""
    _init_users_db()
    defaults = [
        ('sam',  'tothemoon', 'samspisheh@gmail.com'),
        ('hojr', 'hojr1234',  ''),
        ('bot',  'bot',       ''),
    ]
    for uname, pwd, email in defaults:
        if not _get_user(uname):
            _create_user(uname, pwd, email)
            print(f"[Users] Created default user: {uname}", flush=True)

def _send_new_user_email(username: str, email: str, remote_addr: str = ''):
    """Send notification email to Sam when a new user registers."""
    try:
        gmail_pass = os.environ.get('GMAIL_APP_PASSWORD', '').strip()
        if not gmail_pass:
            print(f"[Email] No GMAIL_APP_PASSWORD set — skipping notification", flush=True)
            return
        gmail_user = 'samspisheh@gmail.com'
        body = (
            f"New user registered on Options Trader!\n\n"
            f"Username : {username}\n"
            f"Email    : {email or '(not provided)'}\n"
            f"Time     : {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"IP       : {remote_addr or 'unknown'}\n"
        )
        msg = MIMEText(body)
        msg['Subject'] = f"[Options Trader] New user: {username}"
        msg['From']    = gmail_user
        msg['To']      = gmail_user
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.send_message(msg)
        print(f"[Email] Notification sent for new user: {username}", flush=True)
    except Exception as e:
        print(f"[Email] Failed: {e}", flush=True)


def _current_user() -> str:
    """Return the currently logged-in username from the session (default 'sam')."""
    return (session.get('username') or
            request.headers.get('X-Remote-User', '') or 'sam').lower().strip() or 'sam'


def _get_portfolio(username: str = None) -> Portfolio:
    """Return (and lazily create) the Portfolio for the given user."""
    if username is None:
        username = _current_user()
    with _port_lock:
        if username not in _portfolios:
            db = _data_dir() / f'portfolio_{username}.db'
            p  = Portfolio(db)
            if not p.get_setting('starting_balance'):
                p.set_starting_balance(10_000.0)
            _portfolios[username] = p
    return _portfolios[username]

def _all_portfolios():
    """Return [(username, Portfolio)] for all loaded portfolios."""
    with _port_lock:
        return list(_portfolios.items())

def _init_portfolios():
    """Pre-load portfolios for any DB files that already exist on disk."""
    for db in _data_dir().glob('portfolio_*.db'):
        uname = db.stem.replace('portfolio_', '')
        if uname:
            _get_portfolio(uname)
    _get_portfolio('sam')   # always ensure default user exists

# ── Bot-trading tracker (system-wide, tracks all scanner suggestions) ──────────
_BOT_DB = None   # set in _init_portfolios

def _bot_portfolio() -> Portfolio:
    global _BOT_DB
    if _BOT_DB is None:
        _BOT_DB = Portfolio(_data_dir() / 'portfolio_bot.db')
    return _BOT_DB

# Backward-compat shim so old code still works during refactor
class _PortfolioShim:
    """Proxy that routes calls to the request-scoped user's portfolio."""
    def __getattr__(self, name):
        return getattr(_get_portfolio(), name)

portfolio = _PortfolioShim()

# ── .env loader ────────────────────────────────────────────────────────────────
def _load_env_file():
    env_path = os.path.join(_HERE, '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env_file()

# Paths that never require authentication
_NO_AUTH_PATHS = {
    '/manifest.json', '/sw.js', '/icon-192.png', '/icon-512.png',
    '/api/auth/login', '/api/auth/register',
}

@app.before_request
def _require_session_auth():
    """Session-based auth. Public paths and auth endpoints are always open."""
    p = request.path
    if p in _NO_AUTH_PATHS or p.startswith('/static'):
        return None
    if p == '/':
        return None   # index() decides whether to show login or dashboard
    if 'username' not in session:
        if p.startswith('/api/'):
            return jsonify({'error': 'Not authenticated', 'login_required': True}), 401
        return redirect('/trading/')   # redirect everything else to trading login

# ── Shared state ───────────────────────────────────────────────────────────────
_lock  = threading.Lock()
_state = {
    'ranked':       {'short': [], 'mid': [], 'long': []},
    'prices':       {},      # { TICKER: {price, change, prev} }
    'opt_prices':   {},      # { "TICKER|EXP|STRIKE|TYPE": {bid,ask,...} }
    'vix':          18.5,
    'scan_date':    '',
    'scan_ready':   False,
    'scanning':     False,
    'universe_size': 0,
    'last_price_ts': 0,
    'news': {                # latest market + ticker news
        'market': [], 'tickers': {}, 'sentiment': {}, 'last_updated': 0
    },
}

# ── SSE broadcast ──────────────────────────────────────────────────────────────
_sse_lock    = threading.Lock()
_sse_clients = []   # list of {'username': str, 'queue': queue.Queue}

def broadcast(data: dict, username: str = None):
    """Broadcast to all SSE clients, or only to a specific user if username given."""
    msg = "data: " + json.dumps(data) + "\n\n"
    with _sse_lock:
        dead = []
        for client in _sse_clients:
            if username is None or client['username'] == username:
                try:
                    client['queue'].put_nowait(msg)
                except queue.Full:
                    dead.append(client)
        for c in dead:
            try: _sse_clients.remove(c)
            except ValueError: pass


# ── Scanner ────────────────────────────────────────────────────────────────────

def _do_scan(use_demo: bool):
    """Full market scan — parallel per-ticker, returns ranked dict."""
    if use_demo or not broker.connected:
        universe = generate_universe_demo()
        vix      = 18.5
    else:
        try:
            from data_fetcher import fetch_all
            from universe import TRADEABLE
            raw      = fetch_all(list(TRADEABLE.keys()))
            universe = raw.get('tickers', {})
            vix      = raw.get('vix', 18.5)
        except Exception as e:
            print(f"[Scan] Live fetch failed: {e} — using demo data", flush=True)
            universe = generate_universe_demo()
            vix      = 18.5

    def _scan_one(args):
        ticker, data, tf_key = args
        try:
            return tf_key, scan_ticker(data, tf_key, vix)
        except Exception:
            return tf_key, None

    tasks = [(t, d, tf) for t, d in universe.items() for tf in TIMEFRAMES]

    bucket = {tf: [] for tf in TIMEFRAMES}
    with ThreadPoolExecutor(max_workers=20) as ex:
        for tf, result in ex.map(_scan_one, tasks):
            if result:
                bucket[tf].append(result)

    # Sort each bucket and take top 10
    ranked = {}
    for tf in TIMEFRAMES:
        ranked[tf] = sorted(bucket[tf], key=lambda c: c['score'], reverse=True)[:10]

    return ranked, vix, len(universe)


def _scanner_thread(use_demo: bool, interval: int):
    """Background: scan immediately, then every `interval` seconds."""
    while True:
        with _lock:
            _state['scanning'] = True
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning {79} tickers…", flush=True)
            t0     = time.time()
            ranked, vix, uni_size = _do_scan(use_demo)
            elapsed = time.time() - t0

            today = datetime.now().strftime('%b %d %H:%M')
            with _lock:
                _state['ranked']        = ranked
                _state['vix']           = vix
                _state['scan_date']     = today
                _state['scan_ready']    = True
                _state['scanning']      = False
                _state['universe_size'] = uni_size

            counts = {tf: len(ranked[tf]) for tf in TIMEFRAMES}
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scan done in {elapsed:.1f}s — {counts}", flush=True)

            # Push full scan to all SSE clients
            broadcast({'type': 'scan', 'ranked': ranked,
                        'vix': vix, 'date': today, 'uni': uni_size})

            # Immediately fetch option prices for new candidates
            threading.Thread(target=_fetch_opt_prices, daemon=True).start()

            # Auto-track all scanner suggestions in the bot portfolio
            threading.Thread(target=_bot_track_candidates, args=(ranked,), daemon=True).start()

        except Exception as e:
            print(f"[Scanner] ERROR: {e}", flush=True)
            traceback.print_exc()
            with _lock:
                _state['scanning'] = False

        time.sleep(interval)


# ── Live price + re-ranker ─────────────────────────────────────────────────────

def _fetch_prices_yf(tickers):
    """Fetch latest prices for a list of tickers. Returns {TICKER: {price,change,prev}}."""
    if not tickers:
        return {}
    try:
        import yfinance as yf
        # 1-minute intraday — freshest data yfinance provides
        raw = yf.download(
            ' '.join(sorted(tickers)),
            period='1d', interval='1m',
            progress=False, auto_adjust=True,
            group_by='ticker'
        )
        result = {}
        for tkr in tickers:
            try:
                col = raw['Close'] if len(tickers) == 1 else raw[tkr]['Close']
                col = col.dropna()
                if col.empty:
                    continue
                price = float(col.iloc[-1])
                # prev close: get from 2-day daily data (fast cache-friendly)
                prev  = price   # default fallback
                try:
                    d2  = yf.download(tkr, period='2d', interval='1d', progress=False, auto_adjust=True)
                    c2  = d2['Close'].dropna()
                    if len(c2) >= 2:
                        prev = float(c2.iloc[-2])
                except Exception:
                    pass
                change = (price - prev) / prev * 100 if prev else 0
                result[tkr] = {'price': round(price, 2), 'change': round(change, 2), 'prev': round(prev, 2)}
            except Exception:
                pass
        return result
    except Exception as e:
        print(f"[Prices] {e}", flush=True)
        return {}


def _rerank_with_live_prices(ranked, prices):
    """
    Re-score and re-rank candidates using live stock prices.

    Bonus logic (max ±8 pts):
      - Only apply a meaningful bonus/penalty if daily change > 0.3% (filters out noise)
      - CALL: bonus when stock is up, scaled by change magnitude (capped)
      - PUT:  bonus when stock is down, scaled by change magnitude (capped)
      - Opposite direction: penalty, but softer (don't punish too hard for intraday noise)
    """
    new_ranked = {}
    for tf, candidates in ranked.items():
        adjusted = []
        for c in candidates:
            p = prices.get(c['ticker'])
            if p:
                chg = p['change']          # % daily change (e.g. +1.2 or -0.8)
                is_call = c['option_type'] == 'CALL'

                # Ignore sub-noise moves
                if abs(chg) < 0.3:
                    bonus = 0.0
                else:
                    # Signed alignment: positive if move matches option direction
                    aligned_chg = chg if is_call else -chg
                    if aligned_chg > 0:
                        # Tailwind — graduated bonus: 0.3→1pt, 1%→3pts, 2%→6pts, 3%+→8pts
                        bonus = min(8.0, aligned_chg * 2.5)
                    else:
                        # Headwind — softer penalty (don't over-penalise intraday dips)
                        bonus = max(-5.0, aligned_chg * 1.2)

                live_score = round(c['score'] + bonus, 1)
                adjusted.append({**c, 'live_score': live_score,
                                  'live_price': p['price'], 'live_change': chg})
            else:
                adjusted.append({**c, 'live_score': c['score'],
                                  'live_price': c.get('price', 0), 'live_change': 0})

        adjusted.sort(key=lambda x: x['live_score'], reverse=True)
        new_ranked[tf] = adjusted[:10]
    return new_ranked


_price_thread_running = False

def _price_loop(use_demo: bool):
    """
    Background thread:
      - Every 2s: fetch live prices, broadcast 'prices' event
      - Every 10s: re-rank top 10, broadcast 'ranked' event
    """
    global _price_thread_running
    _price_thread_running = True
    last_rerank = 0

    while True:
        try:
            with _lock:
                ranked = _state['ranked']
                tickers = set()
                for tf in TIMEFRAMES:
                    for c in ranked[tf]:
                        tickers.add(c['ticker'])

            if tickers:
                prices = _fetch_prices_yf(list(tickers))
                if prices:
                    with _lock:
                        _state['prices'] = prices
                        _state['last_price_ts'] = time.time()
                    broadcast({'type': 'prices', 'prices': prices, 'ts': time.time()})

                # Re-rank every 10 seconds
                now = time.time()
                if now - last_rerank >= 10:
                    with _lock:
                        current_ranked  = _state['ranked']
                        current_prices  = _state['prices']
                    new_ranked = _rerank_with_live_prices(current_ranked, current_prices)
                    with _lock:
                        _state['ranked'] = new_ranked
                    broadcast({'type': 'ranked', 'ranked': new_ranked, 'ts': now})
                    last_rerank = now
            else:
                # No tickers yet — send heartbeat so SSE stays alive
                broadcast({'type': 'heartbeat', 'ts': time.time()})

        except Exception as e:
            print(f"[PriceLoop] {e}", flush=True)

        time.sleep(2)


def _fetch_opt_prices():
    """
    Fetch real option bid/ask for all current candidates.
    After fetching, snap each candidate's expiry to the actual yfinance date
    (the real Robinhood-available expiration), then re-broadcast ranked.
    """
    try:
        with _lock:
            ranked = {tf: list(v) for tf, v in _state['ranked'].items()}

        updated      = {}    # key → quote
        expiry_fixes = {}    # old_key → {'new_expiry': '...', 'new_strike': ...}

        for tf, candidates in ranked.items():
            for c in candidates:
                key = f"{c['ticker']}|{c['expiry']}|{c['strike']}|{c['option_type']}"
                opt = _get_option_quote(c['ticker'], c['expiry'], c['strike'], c['option_type'])
                if opt:
                    updated[key] = opt
                    # If yfinance snapped to a different real expiry, record it
                    real_exp = opt.get('actual_expiry')    # e.g. '2025-03-21'
                    if real_exp:
                        try:
                            rd = datetime.strptime(real_exp, '%Y-%m-%d')
                            real_exp_str = rd.strftime('%b %d')
                        except Exception:
                            real_exp_str = real_exp
                        expiry_fixes[key] = {
                            'new_expiry': real_exp_str,
                            'new_strike': opt.get('actual_strike', c['strike']),
                        }
                time.sleep(0.25)   # gentle rate-limit

        if updated:
            with _lock:
                _state['opt_prices'].update(updated)
            broadcast({'type': 'opt_prices', 'data': updated})
            print(f"[Options] Fetched {len(updated)} quotes", flush=True)

        # Sync real expiry dates back into ranked candidates
        if expiry_fixes:
            with _lock:
                for tf in _state['ranked']:
                    for c in _state['ranked'][tf]:
                        old_key = f"{c['ticker']}|{c['expiry']}|{c['strike']}|{c['option_type']}"
                        if old_key in expiry_fixes:
                            fix = expiry_fixes[old_key]
                            c['expiry'] = fix['new_expiry']
                            c['strike'] = fix['new_strike']
                            c['expiry_confirmed'] = True   # flag for UI
                ranked_snapshot = {tf: list(v) for tf, v in _state['ranked'].items()}
            broadcast({'type': 'ranked', 'ranked': ranked_snapshot,
                       'ts': time.time(), 'expiry_synced': True})
            print(f"[Options] Synced {len(expiry_fixes)} real expiry dates", flush=True)

    except Exception as e:
        print(f"[Options] {e}", flush=True)


def _parse_expiry(s):
    for fmt in ('%b %d', '%b %d %Y', '%Y-%m-%d', '%m/%d/%Y'):
        try:
            d = datetime.strptime(s.strip(), fmt)
            if d.year == 1900:
                d = d.replace(year=datetime.now().year)
                if d.date() < date.today():
                    d = d.replace(year=d.year + 1)
            return d.date()
        except ValueError:
            continue
    return None


def _get_option_quote(ticker, expiry_str, strike, opt_type):
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())
        exps = t.options
        if not exps:
            return None
        target = _parse_expiry(expiry_str)
        if not target:
            return None
        closest = min(exps, key=lambda e: abs((datetime.strptime(e, '%Y-%m-%d').date() - target).days))
        chain = t.option_chain(closest)
        df    = chain.calls if opt_type.upper() == 'CALL' else chain.puts
        if df.empty:
            return None
        row = df.iloc[(df['strike'] - float(strike)).abs().argsort().iloc[0]]
        bid  = float(row.get('bid')  or 0)
        ask  = float(row.get('ask')  or 0)
        last = float(row.get('lastPrice') or 0)
        iv   = float(row.get('impliedVolatility') or 0)
        return {
            'bid': round(bid, 2), 'ask': round(ask, 2),
            'mid': round((bid+ask)/2, 2) if (bid or ask) else round(last, 2),
            'last': round(last, 2), 'iv': round(iv * 100, 1),
            'volume': int(row.get('volume') or 0),
            'open_interest': int(row.get('openInterest') or 0),
            'actual_expiry': closest, 'actual_strike': float(row['strike']),
            'ts': time.time(),
        }
    except Exception:
        return None


def _get_live_opt_mid(pos):
    """
    Return the best available live option mid price for an open position.

    Priority:
      1. Fresh quote from _state['opt_prices'] (< 90 s old)
      2. Delta-based estimate from live stock price (fallback)
      3. Last known entry_price (last resort)

    Returns (mid_price, source_label).
    """
    key = f"{pos['ticker']}|{pos['expiry']}|{pos['strike']}|{pos['option_type']}"
    with _lock:
        cached = _state['opt_prices'].get(key)

    if cached:
        bid = cached.get('bid', 0) or 0
        ask = cached.get('ask', 0) or 0
        mid = cached.get('mid') or ((bid + ask) / 2 if (bid or ask) else 0)
        age = time.time() - cached.get('ts', 0)
        if mid > 0 and age < 90:
            return round(mid, 2), 'live'

    # Fallback: delta approximation from live stock price
    ep         = pos['entry_price']
    sp_entry   = pos.get('stock_price_at_entry') or 0
    delta      = abs(pos.get('delta_at_entry') or 0.35)
    opt_type   = (pos.get('option_type') or 'CALL').upper()

    with _lock:
        stock_info = _state['prices'].get(pos['ticker'])

    if stock_info and sp_entry > 0:
        move        = stock_info['price'] - sp_entry
        signed_move = move if opt_type == 'CALL' else -move
        estimated   = max(0.01, round(ep + delta * signed_move, 2))
        return estimated, 'delta_est'

    return ep, 'entry_fallback'


def _refresh_position_opt_prices():
    """Background: every 30 s refresh option quotes for ALL users' open positions."""
    while True:
        time.sleep(30)
        try:
            all_positions = []
            for _, port in _all_portfolios():
                all_positions.extend(port.get_open_positions())
            # Also include bot positions
            all_positions.extend(_bot_portfolio().get_open_positions())
            if not all_positions:
                continue
            updated = {}
            seen = set()
            for pos in all_positions:
                key = f"{pos['ticker']}|{pos['expiry']}|{pos['strike']}|{pos['option_type']}"
                if key in seen:
                    continue
                seen.add(key)
                quote = _get_option_quote(
                    pos['ticker'], pos['expiry'], pos['strike'], pos['option_type']
                )
                if quote:
                    updated[key] = quote
                    time.sleep(0.3)
            if updated:
                with _lock:
                    _state['opt_prices'].update(updated)
                broadcast({'type': 'opt_prices', 'data': updated})
                print(f"[PosOpts] Refreshed {len(updated)} position quotes", flush=True)
        except Exception as e:
            print(f"[PosOpts] {e}", flush=True)


def _check_positions_for_portfolio(username: str, port: Portfolio):
    """Check target/stop for one user's open positions. Called from _position_updater."""
    positions = port.get_open_positions()
    for pos in positions:
        opt_mid, source = _get_live_opt_mid(pos)
        try:
            port.update_current_price(pos['id'], opt_mid)
        except Exception:
            pass
        target = pos['target_price']
        stop   = pos['stop_price']
        ticker = pos['ticker']
        otype  = (pos.get('option_type') or 'CALL').upper()
        if source == 'entry_fallback':
            continue
        if opt_mid >= target:
            port.close_trade(pos['id'], opt_mid, 'target_hit')
            broadcast({'type': 'order_closed', 'id': pos['id'],
                       'reason': 'target_hit', 'exit_price': opt_mid, 'ticker': ticker},
                      username=username)
            broadcast({'type': 'orders', **_orders_payload(port)}, username=username)
            print(f"✓ [{username}] {ticker} {otype}: TARGET ${opt_mid:.2f} [{source}]", flush=True)
        elif opt_mid <= stop:
            port.close_trade(pos['id'], opt_mid, 'stop_hit')
            broadcast({'type': 'order_closed', 'id': pos['id'],
                       'reason': 'stop_hit', 'exit_price': opt_mid, 'ticker': ticker},
                      username=username)
            broadcast({'type': 'orders', **_orders_payload(port)}, username=username)
            print(f"✗ [{username}] {ticker} {otype}: STOP ${opt_mid:.2f} [{source}]", flush=True)


def _position_updater():
    """Checks open positions for ALL users + bot every 5 s."""
    while True:
        time.sleep(5)
        try:
            for username, port in _all_portfolios():
                _check_positions_for_portfolio(username, port)
            # Also monitor bot positions
            _check_positions_for_portfolio('_bot', _bot_portfolio())
        except Exception as e:
            print(f"[Positions] {e}", flush=True)


# ── Bot trading: auto-track scanner suggestions ────────────────────────────────

def _is_market_hours() -> bool:
    """Return True if US equity market is currently open (Mon–Fri 9:30–16:00 ET)."""
    try:
        import pytz
        et  = pytz.timezone('US/Eastern')
        now = datetime.now(et)
        if now.weekday() >= 5:   # Saturday=5, Sunday=6
            return False
        market_open  = now.replace(hour=9,  minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0,  second=0, microsecond=0)
        return market_open <= now <= market_close
    except Exception:
        # pytz not installed — fall back to UTC heuristic
        now = datetime.utcnow()
        if now.weekday() >= 5:
            return False
        # 13:30–20:00 UTC ≈ 9:30–16:00 ET (ignores DST)
        h, m = now.hour, now.minute
        return (h > 13 or (h == 13 and m >= 30)) and h < 20


def _bot_track_candidates(ranked: dict):
    """
    After every scan, record paper trades for any new top-10 suggestion:
      - Only during market hours
      - No duplicate open positions (same ticker + option_type + strike)
      - Separate lists per timeframe (short / mid / long)
      - Entry = scanner's suggested entry (or live mid if fresher)
      - Target and stop from scanner suggestions
    """
    if not _is_market_hours():
        print("[Bot] Market closed — skipping auto-tracking", flush=True)
        return

    bot = _bot_portfolio()

    # Build set of keys already open in the bot portfolio
    open_positions = bot.get_open_positions()
    open_keys: set = set()
    for pos in open_positions:
        # Dedup by ticker+option_type+strike (ignore expiry drift)
        open_keys.add(f"{pos['ticker']}|{pos.get('option_type','')}|{pos.get('strike',0)}")

    now = datetime.utcnow().isoformat()
    for tf, candidates in ranked.items():
        for c in candidates:
            # Dedup key: ticker + option_type + strike  (per timeframe to allow
            # the same option to appear in both short and mid lists independently)
            dedup = f"{c['ticker']}|{c.get('option_type','')}|{c.get('strike',0)}|{tf}"
            open_key = f"{c['ticker']}|{c.get('option_type','')}|{c.get('strike',0)}"

            # Skip if there's already an open position for this option
            if open_key in open_keys:
                continue

            # Skip if we already queued this exact option in a previous scan
            # (will be re-eligible once the position closes)
            with _port_lock:
                pass   # nothing to lock here, just a note

            # Get the best available entry price (live mid > scanner suggestion)
            entry = c.get('entry', 0)
            opt_key_str = f"{c['ticker']}|{c.get('expiry','')}|{c.get('strike','')}|{c.get('option_type','')}"
            with _lock:
                opt_cache = _state['opt_prices'].get(opt_key_str)
            if opt_cache:
                mid = opt_cache.get('mid', 0) or 0
                age = time.time() - opt_cache.get('ts', 0)
                if mid > 0 and age < 90:
                    entry = mid

            if entry <= 0:
                continue   # no valid price — skip

            try:
                bot.record_trade({
                    'ticker':          c['ticker'],
                    'option_type':     c.get('option_type', 'CALL'),
                    'strike':          c.get('strike', 0),
                    'expiry':          c.get('expiry', ''),
                    'dte':             c.get('dte', 0),
                    'contracts':       1,
                    'entry_price':     entry,
                    'target_price':    c.get('target', 0),
                    'stop_price':      c.get('stop', 0),
                    'stock_price':     c.get('price', 0),
                    'iv':              c.get('iv', 0),
                    'delta':           c.get('delta', 0),
                    'score':           c.get('score', 0),
                    'timeframe':       tf,
                    'mode':            'bot',
                    'opened_at':       now,
                    'alpaca_order_id': f'BOT-{tf[:1].upper()}-{int(time.time())}',
                    'notes':           f'Bot auto-trade ({tf}) — {now[:10]}',
                    'metadata':        {'tf': tf},
                })
                open_keys.add(open_key)   # mark as open so we don't double-add this scan
                print(f"[Bot] {tf} → {c['ticker']} {c.get('option_type')} "
                      f"${c.get('strike')} entry=${entry:.2f} "
                      f"target=${c.get('target',0):.2f} stop=${c.get('stop',0):.2f}",
                      flush=True)
            except Exception as ex:
                print(f"[Bot] Failed to record {c['ticker']}: {ex}", flush=True)


# ── News engine ────────────────────────────────────────────────────────────────

_BULL_WORDS = {
    'beat','beats','surge','surged','surging','jump','jumped','rally','rallied','record',
    'upgrade','upgraded','buy','strong','strength','growth','profit','gain','gains','rise',
    'rose','soar','soared','climb','climbed','lifted','boost','boosted','bullish','exceed',
    'exceeded','above','outperform','outperformed','accelerate','expanded','expansion',
    'breakout','momentum','positive','recovery','rebound','upside','raises','raised',
    'higher','high','top','record-high','increase','increased','improving','opportunity',
}
_BEAR_WORDS = {
    'miss','missed','misses','drop','dropped','fall','fell','decline','declined','warning',
    'downgrade','downgraded','sell','weak','weakness','loss','losses','cut','cuts','plunge',
    'plunged','concern','concerns','fear','fears','below','bearish','crash','crashed',
    'slump','slumped','disappoint','disappointed','disappointing','risk','risks','threat',
    'negative','trouble','worry','slowdown','recession','layoff','layoffs','shortage',
    'inflation','tariff','tariffs','uncertainty','lower','downside','worsening','deficit',
    'sues','lawsuit','fraud','investigation','recall','halt','suspended',
}

def _simple_sentiment(title: str, summary: str = '') -> str:
    """Keyword-based sentiment: bullish / bearish / neutral."""
    text  = (title + ' ' + (summary or '')).lower()
    words = set(text.replace(',', '').replace('.', '').replace('!', '').split())
    bull  = len(words & _BULL_WORDS)
    bear  = len(words & _BEAR_WORDS)
    if bull > bear:    return 'bullish'
    if bear > bull:    return 'bearish'
    return 'neutral'


def _extract_news_item(n: dict):
    """
    Robustly extract a standardised news item from a yfinance raw article dict.
    Handles ALL known yfinance response formats:
      - 0.1.x / 0.2.x:  flat dict with 'title', 'link', 'publisher', etc.
      - 0.2.50+:         wrapped under a 'content' sub-dict with camelCase keys
    Returns None if the item has no usable title.
    """
    if not isinstance(n, dict):
        return None

    # yfinance 0.2.50+ wraps the actual data under a 'content' key
    # e.g. {'id': '...', 'contentType': 'STORY', 'content': {'title': ..., 'url': ..., ...}}
    inner = n.get('content')
    if isinstance(inner, dict) and inner.get('title'):
        n = inner  # unwrap — work with the inner dict for all lookups below

    # ── Title (required) ──────────────────────────────────────────────────────
    title = ''
    for k in ('title', 'headline', 'Title', 'name', 'displayName'):
        v = n.get(k)
        if isinstance(v, str) and v.strip():
            title = v.strip(); break
    if not title:
        return None

    # ── Summary ───────────────────────────────────────────────────────────────
    summary = ''
    for k in ('summary', 'description', 'snippet', 'body', 'Summary', 'contentText'):
        v = n.get(k)
        if isinstance(v, str) and len(v.strip()) > 20:
            summary = v.strip()[:500]; break
    # 'content' key at top level sometimes holds the body text (old format)
    if not summary:
        v = n.get('content')
        if isinstance(v, str) and len(v.strip()) > 20:
            summary = v.strip()[:500]

    # ── URL ───────────────────────────────────────────────────────────────────
    url = ''
    for k in ('link', 'url', 'canonicalUrl', 'clickThroughUrl', 'Link'):
        v = n.get(k)
        if isinstance(v, dict):
            v = v.get('url', '') or v.get('value', '')
        if isinstance(v, str) and v.startswith('http'):
            url = v; break

    # ── Publisher ─────────────────────────────────────────────────────────────
    publisher = ''
    for k in ('publisher', 'source', 'provider', 'Publisher', 'sourceWebsite'):
        v = n.get(k)
        if isinstance(v, dict):
            v = v.get('displayName', '') or v.get('name', '')
        if isinstance(v, str) and v.strip():
            publisher = v.strip(); break

    # ── Published timestamp (Unix seconds) ───────────────────────────────────
    published = 0
    for k in ('providerPublishTime', 'published', 'pubDate', 'time',
              'timestamp', 'Published', 'publishedAt', 'datePublished', 'pubtime'):
        v = n.get(k)
        if v:
            if isinstance(v, (int, float)) and v > 1_000_000_000:
                published = int(v); break
            if isinstance(v, str):
                try:
                    from datetime import datetime as _dt
                    published = int(_dt.fromisoformat(
                        v.replace('Z', '+00:00').replace('z', '+00:00')
                    ).timestamp()); break
                except Exception:
                    pass

    tickers = n.get('relatedTickers') or n.get('tickers') or []
    if isinstance(tickers, str):
        tickers = [tickers]

    return {
        'title':     title,
        'summary':   summary,
        'url':       url,
        'publisher': publisher,
        'published': published,
        'sentiment': _simple_sentiment(title, summary),
        'tickers':   list(tickers),
    }


def _rss_news(symbol: str, max_items: int = 8) -> list:
    """
    Fetch news via Yahoo Finance RSS feed using stdlib urllib (no extra deps).
    Used as fallback when yfinance .news returns empty.
    """
    try:
        from urllib import request as _ureq
        import xml.etree.ElementTree as _ET
        url = (f"https://feeds.finance.yahoo.com/rss/2.0/headline"
               f"?s={symbol}&region=US&lang=en-US")
        req = _ureq.Request(url, headers={
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 Chrome/124 Safari/537.36'),
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
        })
        with _ureq.urlopen(req, timeout=8) as resp:
            xml_bytes = resp.read()

        root = _ET.fromstring(xml_bytes)
        items, seen = [], set()
        for elem in root.findall('.//item'):
            t = (elem.findtext('title') or '').strip()
            if not t or t in seen:
                continue
            seen.add(t)
            desc   = (elem.findtext('description') or '').strip()[:500]
            lnk    = (elem.findtext('link') or '').strip()
            pd_str = (elem.findtext('pubDate') or '').strip()
            pub_ts = 0
            if pd_str:
                try:
                    from email.utils import parsedate_to_datetime as _p2dt
                    pub_ts = int(_p2dt(pd_str).timestamp())
                except Exception:
                    pass
            src = elem.find('source')
            pub_name = (src.text or '').strip() if src is not None else ''
            items.append({
                'title':     t,
                'summary':   desc,
                'url':       lnk,
                'publisher': pub_name,
                'published': pub_ts,
                'sentiment': _simple_sentiment(t, desc),
                'tickers':   [symbol],
            })
            if len(items) >= max_items:
                break
        return sorted(items, key=lambda x: x['published'], reverse=True)
    except Exception as e:
        print(f"[News] RSS fallback failed for {symbol}: {type(e).__name__}: {e}", flush=True)
        return []


def _yf_news(symbol: str, max_items: int = 8) -> list:
    """
    Fetch and clean news for a single symbol.
    Tries multiple methods in order:
      1. yfinance .news property (all versions, including 0.2.50+ 'content' wrapper)
      2. yfinance .get_news() method (available in some newer builds)
      3. Direct Yahoo Finance RSS via urllib (stdlib, no extra deps)
    Returns a deduplicated, time-sorted list of standardised news items.
    """
    # ── Method 1 & 2: yfinance ────────────────────────────────────────────────
    try:
        import yfinance as yf
        tkr = yf.Ticker(symbol)

        raw = None
        # Try .news attribute first
        try:
            raw = tkr.news
        except Exception:
            pass

        # Some builds wrap news under a dict — unwrap
        if isinstance(raw, dict):
            raw = raw.get('news', raw.get('items', raw.get('stories', [])))

        # If still empty, try get_news() method (newer yfinance)
        if not raw:
            try:
                raw = tkr.get_news()
            except Exception:
                pass

        # Normalise: some versions return a generator
        if raw is not None and not isinstance(raw, list):
            try:
                raw = list(raw)
            except Exception:
                raw = []

        if raw and len(raw) > 0:
            items, seen = [], set()
            for n in raw[:max_items * 2]:
                item = _extract_news_item(n)
                if item and item['title'] not in seen:
                    seen.add(item['title'])
                    items.append(item)
                    if len(items) >= max_items:
                        break
            if items:
                print(f"[News] yfinance OK for {symbol}: {len(items)} items", flush=True)
                return sorted(items, key=lambda x: x['published'], reverse=True)
    except Exception as e:
        print(f"[News] yfinance failed for {symbol}: {type(e).__name__}: {e}", flush=True)

    # ── Method 3: Yahoo Finance RSS ───────────────────────────────────────────
    print(f"[News] Trying RSS fallback for {symbol}…", flush=True)
    rss = _rss_news(symbol, max_items)
    if rss:
        print(f"[News] RSS OK for {symbol}: {len(rss)} items", flush=True)
    return rss


def _fetch_market_rss_fallback(seen_titles: set) -> list:
    """
    Extra RSS feeds for market news when ETF proxies return nothing.
    Uses only stdlib urllib — no extra dependencies.
    """
    fallback_feeds = [
        ('MarketWatch', 'https://feeds.marketwatch.com/marketwatch/topstories/'),
        ('CNBC',        'https://www.cnbc.com/id/100003114/device/rss/rss.html'),
        ('Reuters',     'https://feeds.reuters.com/reuters/businessNews'),
        ('Investopedia','https://www.investopedia.com/feedbuilder/feed/getfeed?feedName=rss_headline'),
    ]
    items = []
    try:
        from urllib import request as _ureq
        import xml.etree.ElementTree as _ET
        for feed_name, feed_url in fallback_feeds:
            try:
                req = _ureq.Request(feed_url, headers={
                    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                   'AppleWebKit/537.36 Chrome/124 Safari/537.36'),
                    'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                })
                with _ureq.urlopen(req, timeout=6) as resp:
                    xml_bytes = resp.read()
                root = _ET.fromstring(xml_bytes)
                for elem in root.findall('.//item'):
                    t = (elem.findtext('title') or '').strip()
                    if not t or t in seen_titles:
                        continue
                    seen_titles.add(t)
                    desc = (elem.findtext('description') or '').strip()[:500]
                    lnk  = (elem.findtext('link') or '').strip()
                    pd_s = (elem.findtext('pubDate') or '').strip()
                    pub_ts = 0
                    if pd_s:
                        try:
                            from email.utils import parsedate_to_datetime as _p2d
                            pub_ts = int(_p2d(pd_s).timestamp())
                        except Exception:
                            pass
                    items.append({
                        'title':     t,
                        'summary':   desc,
                        'url':       lnk,
                        'publisher': feed_name,
                        'published': pub_ts,
                        'sentiment': _simple_sentiment(t, desc),
                        'tickers':   [],
                    })
                    if len(items) >= 12:
                        break
                if len(items) >= 12:
                    break
                print(f"[News] Market RSS {feed_name}: {len(items)} items so far", flush=True)
            except Exception as fe:
                print(f"[News] Market RSS {feed_name} failed: {fe}", flush=True)
    except Exception as e:
        print(f"[News] Market RSS fallback error: {e}", flush=True)
    return items


def _fetch_news():
    """
    Fetch market-wide + per-ticker news via yfinance (Yahoo Finance).
    Falls back to direct RSS feeds when yfinance returns nothing.
    Results pushed to all SSE clients as {'type': 'news', ...}.
    """
    try:
        # ── 1. Market news via broad-market ETF proxies ───────────────────────
        market_news: list = []
        seen_titles: set  = set()
        for proxy in ('SPY', 'QQQ', 'IWM', 'DIA'):
            items = _yf_news(proxy, max_items=5)
            for item in items:
                if item['title'] not in seen_titles:
                    seen_titles.add(item['title'])
                    market_news.append(item)
            time.sleep(0.4)

        # If ETF proxies returned nothing, try direct RSS feeds
        if not market_news:
            print("[News] ETF proxies returned nothing — trying market RSS feeds…", flush=True)
            extra = _fetch_market_rss_fallback(seen_titles)
            market_news.extend(extra)

        market_news.sort(key=lambda x: x['published'], reverse=True)
        market_news = market_news[:14]
        print(f"[News] Market: {len(market_news)} articles", flush=True)

        # ── 2. Per-ticker news for all current ranked candidates ──────────────
        with _lock:
            ranked = {tf: list(v) for tf, v in _state['ranked'].items()}

        tickers: set = set()
        for tf_cands in ranked.values():
            for c in tf_cands:
                tickers.add(c['ticker'])

        if not tickers:
            print("[News] No ranked tickers yet — only market news fetched", flush=True)

        ticker_news:  dict = {}
        ticker_senti: dict = {}

        for tkr in sorted(tickers)[:25]:
            items = _yf_news(tkr, max_items=6)
            ticker_news[tkr]  = items
            bulls = sum(1 for i in items if i['sentiment'] == 'bullish')
            bears = sum(1 for i in items if i['sentiment'] == 'bearish')
            ticker_senti[tkr] = ('bullish' if bulls > bears
                                 else 'bearish' if bears > bulls else 'neutral')
            print(f"[News]   {tkr}: {len(items)} articles → {ticker_senti[tkr]}", flush=True)
            time.sleep(0.25)

        # ── 3. Overall market sentiment ───────────────────────────────────────
        m_bulls  = sum(1 for n in market_news if n['sentiment'] == 'bullish')
        m_bears  = sum(1 for n in market_news if n['sentiment'] == 'bearish')
        overall  = ('bullish' if m_bulls > m_bears
                    else 'bearish' if m_bears > m_bulls else 'neutral')
        ticker_senti['_market'] = overall

        news_payload = {
            'market':       market_news,
            'tickers':      ticker_news,
            'sentiment':    ticker_senti,
            'last_updated': time.time(),
        }
        with _lock:
            _state['news'] = news_payload

        broadcast({'type': 'news', **news_payload})
        print(f"[News] Done — market={overall}, tickers={len(ticker_news)}", flush=True)

    except Exception as e:
        import traceback
        print(f"[News] fetch error: {e}", flush=True)
        traceback.print_exc()


def _news_thread():
    """
    Background thread: wait for the first market scan to complete (so we
    have ranked tickers), then fetch news immediately and every 5 minutes.
    """
    print("[News] Waiting for first scan before fetching news…", flush=True)
    for _ in range(60):          # wait up to 5 min
        with _lock:
            ready = _state['scan_ready']
        if ready:
            break
        time.sleep(5)

    print("[News] Starting first news fetch…", flush=True)
    _fetch_news()

    while True:
        time.sleep(120)   # refresh every 2 minutes
        _fetch_news()


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'username' not in session:
        return send_from_directory(_HERE, 'login.html')
    return send_from_directory(_HERE, 'dashboard.html')


# ── Auth endpoints ──────────────────────────────────────────────────────────────

@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    data     = request.get_json() or {}
    username = data.get('username', '').lower().strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    user = _get_user(username)
    if not user or not _verify_password(user['password_hash'], password):
        return jsonify({'error': 'Invalid username or password'}), 401
    session['username'] = username
    session.permanent   = True
    _get_portfolio(username)   # ensure portfolio exists
    return jsonify({'success': True, 'username': username})


@app.route('/api/auth/register', methods=['POST'])
def api_auth_register():
    data     = request.get_json() or {}
    username = data.get('username', '').lower().strip()
    password = data.get('password', '')
    email    = data.get('email', '').strip()
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400
    if len(password) < 4:
        return jsonify({'error': 'Password must be at least 4 characters'}), 400
    if not _create_user(username, password, email):
        return jsonify({'error': 'Username already taken'}), 409
    session['username'] = username
    session.permanent   = True
    _get_portfolio(username)   # create fresh portfolio
    remote_addr = request.headers.get('X-Forwarded-For', request.remote_addr or '')
    threading.Thread(target=_send_new_user_email,
                     args=(username, email, remote_addr), daemon=True).start()
    return jsonify({'success': True, 'username': username})


@app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    session.clear()
    return jsonify({'success': True})


@app.route('/api/auth/me')
def api_auth_me():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not authenticated'}), 401
    return jsonify({'username': username})


@app.route('/manifest.json')
def pwa_manifest():
    return send_from_directory(_HERE, 'manifest.json',
                               mimetype='application/manifest+json')


@app.route('/sw.js')
def pwa_sw():
    resp = send_from_directory(_HERE, 'sw.js', mimetype='application/javascript')
    # Service workers must be served without cache for immediate updates
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp


def _pwa_icon_svg():
    """Return a simple green-chart SVG used as the app icon."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192">'
        '<rect width="192" height="192" rx="32" fill="#0d1117"/>'
        '<polyline points="20,140 60,90 100,110 140,50 172,70" '
        'fill="none" stroke="#3fb950" stroke-width="10" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        '<circle cx="172" cy="70" r="8" fill="#3fb950"/>'
        '</svg>'
    )
    return Response(svg, mimetype='image/svg+xml')

@app.route('/icon-192.png')
def pwa_icon_192():
    return _pwa_icon_svg()

@app.route('/icon-512.png')
def pwa_icon_512():
    return _pwa_icon_svg()


@app.route('/api/stream')
def api_stream():
    """SSE endpoint — browser connects once, receives all updates."""
    username = _current_user()
    port = _get_portfolio(username)
    q    = queue.Queue(maxsize=60)
    client = {'username': username, 'queue': q}
    with _sse_lock:
        _sse_clients.append(client)

    # Snapshot current state for immediate delivery
    with _lock:
        init = {
            'type':       'init',
            'ranked':     _state['ranked'],
            'prices':     _state['prices'],
            'opt_prices': _state['opt_prices'],
            'vix':        _state['vix'],
            'date':       _state['scan_date'],
            'scan_ready': _state['scan_ready'],
            'scanning':   _state['scanning'],
            'uni':        _state['universe_size'],
            'news':       _state.get('news', {}),
            'orders': {
                'open':    port.get_open_positions(),
                'closed':  port.get_closed_trades(200),
                'summary': port.get_summary(),
            }
        }

    def generate():
        yield "data: " + json.dumps(init) + "\n\n"
        try:
            while True:
                try:
                    msg = q.get(timeout=25)
                    yield msg
                except queue.Empty:
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            pass
        finally:
            with _sse_lock:
                try: _sse_clients.remove(client)
                except ValueError: pass

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no',
                 'Connection': 'keep-alive'}
    )


@app.route('/api/chart/<ticker>')
def api_chart(ticker):
    try:
        import yfinance as yf
        from datetime import datetime as _dt, timedelta as _td
        t    = yf.Ticker(ticker.upper())
        # Use actual traded prices (auto_adjust=False) to avoid split/dividend
        # distortions that make historical bars look wildly wrong.
        # Fetch 90 calendar days so we always have ≥60 trading days to work with.
        _end   = _dt.today()
        _start = _end - _td(days=90)
        hist = t.history(start=_start, end=_end, interval='1d', auto_adjust=False)
        if hist.empty:
            # fallback: try period-based fetch
            hist = t.history(period='3mo', interval='1d', auto_adjust=False)
        if hist.empty:
            return jsonify({'error': 'No data'}), 404
        hist.index = hist.index.tz_localize(None) if getattr(hist.index,'tzinfo',None) else hist.index
        closes = [round(float(v), 2) for v in hist['Close'] if float(v) > 0]
        # Keep only the last 63 trading days
        closes = closes[-63:]
        # Anchor filter: drop any bar outside ±35% of the most-recent close
        # (catches any remaining data artifacts)
        if len(closes) >= 2:
            ref = closes[-1]
            closes = [c for c in closes if 0.65 * ref <= c <= 1.35 * ref]
        sma20  = [None]*len(closes)
        for i in range(19, len(closes)):
            sma20[i] = round(sum(closes[i-19:i+1])/20, 2)
        # Intraday (1m) for today's live line
        intra  = t.history(period='1d', interval='1m', auto_adjust=True)
        itimes, icloses = [], []
        if not intra.empty:
            intra.index = intra.index.tz_localize(None) if getattr(intra.index,'tzinfo',None) else intra.index
            icloses = [round(float(v),2) for v in intra['Close'].dropna()]
            itimes  = [str(d) for d in intra.index]
        # Dates: align with filtered closes (take last N from hist.index)
        all_dates = [str(d.date()) for d in hist.index if True]
        dates = all_dates[-len(closes):]
        return jsonify({
            'ticker': ticker.upper(),
            'dates':  dates,
            'closes': closes, 'sma20': sma20,
            'volumes':[int(v) for v in hist['Volume']],
            'intraday_closes': icloses, 'intraday_times': itimes,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/option_quote/<ticker>/<path:expiry>/<strike>/<opt_type>')
def api_option_quote(ticker, expiry, strike, opt_type):
    r = _get_option_quote(ticker, expiry, float(strike), opt_type)
    return jsonify(r) if r else (jsonify({'error':'no data'}), 404)


def _orders_payload(port=None):
    """Build the full orders+account snapshot sent to the client."""
    if port is None:
        port = _get_portfolio()
    open_pos = port.get_open_positions()
    closed   = port.get_closed_trades(200)
    summary  = port.get_summary()
    for p in open_pos:
        oid = p.get('alpaca_order_id') or ''
        p['display_status'] = 'DEMO'    if oid.startswith('DEMO-')    else \
                              'PENDING' if oid.startswith('PENDING-') else 'OPEN'
    summary.setdefault('open_count',   summary.get('open_positions', len(open_pos)))
    summary.setdefault('closed_count', summary.get('closed_trades',  len(closed)))
    return {
        'open':      open_pos,
        'closed':    closed,
        'summary':   summary,
        'broker':    broker.mode,
        'connected': broker.connected,
    }


@app.route('/api/news')
def api_news():
    """Return current news state. Triggers a background refresh if stale (> 6 min)."""
    with _lock:
        news = dict(_state.get('news', {}))
    if not news or time.time() - news.get('last_updated', 0) > 360:
        threading.Thread(target=_fetch_news, daemon=True).start()
    return jsonify(news)


@app.route('/api/news/refresh', methods=['POST'])
def api_news_refresh():
    """Force an immediate news refresh."""
    threading.Thread(target=_fetch_news, daemon=True).start()
    return jsonify({'status': 'refreshing'})


@app.route('/api/news/debug/<symbol>')
def api_news_debug(symbol):
    """Debug endpoint: show raw yfinance news + RSS fallback diagnostics for a symbol."""
    sym = symbol.upper()
    result = {'symbol': sym, 'yfinance': {}, 'rss': {}, 'final': []}

    # ── yfinance probe ────────────────────────────────────────────────────────
    try:
        import yfinance as yf
        tkr = yf.Ticker(sym)

        raw_news_attr = None
        err_attr = None
        try:
            raw_news_attr = tkr.news
        except Exception as e:
            err_attr = str(e)

        raw_get_news = None
        err_get = None
        try:
            raw_get_news = tkr.get_news()
        except Exception as e:
            err_get = str(e)

        result['yfinance'] = {
            'version':       getattr(yf, '__version__', 'unknown'),
            'news_attr_type': type(raw_news_attr).__name__,
            'news_attr_len':  len(raw_news_attr) if isinstance(raw_news_attr, (list,dict)) else None,
            'news_attr_err':  err_attr,
            'news_attr_first': raw_news_attr[0] if isinstance(raw_news_attr, list) and raw_news_attr else None,
            'get_news_type':  type(raw_get_news).__name__,
            'get_news_len':   len(raw_get_news) if isinstance(raw_get_news, (list,dict)) else None,
            'get_news_err':   err_get,
            'get_news_first': raw_get_news[0] if isinstance(raw_get_news, list) and raw_get_news else None,
        }
    except Exception as e:
        result['yfinance']['import_error'] = str(e)

    # ── RSS probe ─────────────────────────────────────────────────────────────
    rss_items = _rss_news(sym, max_items=3)
    result['rss'] = {
        'count': len(rss_items),
        'first': rss_items[0] if rss_items else None,
    }

    # ── Full pipeline result ──────────────────────────────────────────────────
    result['final'] = _yf_news(sym, max_items=5)
    return jsonify(result)


@app.route('/api/account')
def api_account():
    """Return current account balance state."""
    return jsonify(_get_portfolio().get_account_balance())


@app.route('/api/state')
def api_state():
    """
    Mobile / polling API — returns the full current scanner state in one shot.
    Clients can poll this every 5 s instead of maintaining an SSE connection.
    """
    with _lock:
        ranked     = {k: list(v) for k, v in _state.get('ranked', {}).items()}
        prices     = dict(_state.get('prices', {}))
        opt_prices = dict(_state.get('opt_prices', {}))
        scan_ready = bool(_state.get('scan_ready', False))
        scan_time  = _state.get('scan_time', 0)
    return jsonify({
        'ranked':     ranked,
        'prices':     prices,
        'opt_prices': opt_prices,
        'scan_ready': scan_ready,
        'scan_time':  scan_time,
    })


@app.route('/api/orders')
def api_orders():
    return jsonify(_orders_payload())


@app.route('/api/order', methods=['POST'])
def api_order():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400
    required = ['ticker','option_type','strike','expiry','contracts',
                'entry_price','target_price','stop_price']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Missing: {missing}'}), 400

    # ── Enforce account balance — cannot spend more than available cash ──────
    order_cost = float(data['entry_price']) * int(data.get('contracts', 1)) * 100
    acct       = portfolio.get_account_balance()
    if order_cost > acct['available_cash']:
        return jsonify({
            'error':     (f"Insufficient funds — this order costs ${order_cost:,.2f} "
                          f"but you only have ${acct['available_cash']:,.2f} available cash."),
            'available': acct['available_cash'],
            'needed':    order_cost,
            'code':      'insufficient_funds',
        }), 400

    # ── Build enriched metadata ───────────────────────────────────────────────
    import json as _json
    existing_meta = {}
    if 'metadata' in data and isinstance(data['metadata'], dict):
        existing_meta = data['metadata']
    enriched_meta = {
        **existing_meta,
        # target_price / stop_price = OPTION prices — the monitor compares opt_mid against these
        'option_target': data.get('target_price'),    # same as target_price, for display
        'option_stop':   data.get('stop_price'),      # same as stop_price,  for display
        'stock_target':  data.get('stock_target'),    # stock price reference (from screener)
        'stock_stop':    data.get('stock_stop'),      # stock price reference (from screener)
    }

    result = broker.place_option_order(data)
    if result.get('status') in ('submitted', 'pending_new', 'demo_placed'):
        trade_id = portfolio.record_trade({
            **data,
            'metadata':        enriched_meta,
            'alpaca_order_id': result.get('order_id', f"DEMO-{int(time.time())}"),
            'mode': 'paper' if broker.cfg.get('paper', True) else 'live',
        })
        payload = _orders_payload()
        broadcast({'type': 'orders', **payload})
        return jsonify({'success': True, 'trade_id': trade_id, **result})
    return jsonify({'success': False, **result}), 500


@app.route('/api/close/<int:trade_id>', methods=['POST'])
def api_close(trade_id):
    port       = _get_portfolio()
    data       = request.get_json() or {}
    exit_price = data.get('exit_price', 0)
    positions  = port.get_open_positions()
    pos = next((p for p in positions if p['id'] == trade_id), None)
    if not pos:
        return jsonify({'error': 'Not found'}), 404
    if not exit_price:
        exit_price = pos.get('current_price') or pos['entry_price']
    broker.close_position(alpaca_order_id=pos.get('alpaca_order_id'), ticker=pos['ticker'])
    port.close_trade(trade_id, exit_price, 'manual')
    username = _current_user()
    payload = _orders_payload(port)
    broadcast({'type': 'orders', **payload}, username=username)
    return jsonify({'success': True, 'exit_price': exit_price})


@app.route('/api/bot_trades')
def api_bot_trades():
    """Return bot portfolio performance — all auto-tracked scanner suggestions."""
    bot = _bot_portfolio()
    open_pos = bot.get_open_positions()
    closed   = bot.get_closed_trades(500)
    summary  = bot.get_summary()
    # Annotate current unrealized P&L for open positions
    total_unrealized = sum(p.get('unrealized_pnl', 0) for p in open_pos)
    wins   = summary.get('wins', 0)
    losses = summary.get('losses', 0)
    total  = wins + losses
    return jsonify({
        'open':           open_pos,
        'closed':         closed,
        'total_open':     len(open_pos),
        'total_closed':   total,
        'wins':           wins,
        'losses':         losses,
        'win_rate':       round(wins / total * 100, 1) if total else 0,
        'realized_pnl':   summary.get('realized_pnl', 0),
        'unrealized_pnl': round(total_unrealized, 2),
        'total_pnl':      round(summary.get('realized_pnl', 0) + total_unrealized, 2),
    })


@app.route('/api/admin/fix_trades', methods=['POST'])
def api_admin_fix_trades():
    """Delete trades with suspicious realized gain (exit_price unreasonably high)."""
    port = _get_portfolio()
    deleted = []
    with sqlite3.connect(str(port.db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, ticker, entry_price, exit_price, status FROM trades "
            "WHERE status='closed' AND exit_price > entry_price * 10"
        ).fetchall()
        for r in rows:
            conn.execute("DELETE FROM trades WHERE id=?", (r['id'],))
            deleted.append({'id': r['id'], 'ticker': r['ticker'],
                            'entry': r['entry_price'], 'exit': r['exit_price']})
    username = _current_user()
    broadcast({'type': 'orders', **_orders_payload(port)}, username=username)
    return jsonify({'deleted': deleted, 'count': len(deleted)})


@app.route('/api/admin/clear_demo_trades', methods=['POST'])
def api_admin_clear_demo_trades():
    """Delete all DEMO / auto-generated trades from the current user's portfolio."""
    port     = _get_portfolio()
    username = _current_user()
    deleted  = []
    with sqlite3.connect(str(port.db_path)) as conn:
        conn.row_factory = sqlite3.Row
        # Demo trades: alpaca_order_id starts with DEMO- or mode='demo'
        rows = conn.execute(
            "SELECT id, ticker, status, alpaca_order_id, notes FROM trades "
            "WHERE alpaca_order_id LIKE 'DEMO-%' OR mode='demo' OR notes LIKE '%demo%'"
        ).fetchall()
        for r in rows:
            conn.execute("DELETE FROM trades WHERE id=?", (r['id'],))
            deleted.append({'id': r['id'], 'ticker': r['ticker']})
        conn.commit()
    broadcast({'type': 'orders', **_orders_payload(port)}, username=username)
    print(f"[Admin] Cleared {len(deleted)} demo trades for {username}", flush=True)
    return jsonify({'deleted': deleted, 'count': len(deleted)})


# ── Main ───────────────────────────────────────────────────────────────────────

def _migrate_corrupt_trades():
    """
    One-time fix for trades where the position monitor incorrectly recorded
    exit_price = option_target_price (e.g. $2.26) because it compared a STOCK
    price against an OPTION-level target.

    Pattern of corrupt record:
      - auto-closed (exit_reason = target_hit / stop_hit)
      - exit_price == target_price  (the 'target' column stored option target)
      - target_price < 20           (definitely an option price, not a stock)
      - entry_price < 10            (option premium, not stock price)

    These records are flagged with a warning note in the DB. P&L calculations
    for them will be inaccurate. The user is advised to manually close and
    re-open them if needed.
    """
    try:
        import json as _json
        with portfolio._conn() as conn:
            rows = conn.execute("""
                SELECT id, ticker, entry_price, exit_price, target_price, stop_price,
                       stock_price_at_entry, delta_at_entry, exit_reason, metadata, notes
                FROM trades
                WHERE status = 'closed'
                  AND exit_reason IN ('target_hit', 'stop_hit')
                  AND ABS(exit_price - target_price) < 0.01
                  AND target_price < 20
                  AND entry_price < 10
                  AND (metadata IS NULL OR metadata NOT LIKE '%"data_fix"%')
            """).fetchall()

            if not rows:
                return

            print(f"[Migration] Flagging {len(rows)} trade(s) with suspect exit prices...", flush=True)
            for r in rows:
                try:
                    meta = _json.loads(r['metadata'] or '{}')
                except Exception:
                    meta = {}
                meta['data_fix'] = ('exit_price was incorrectly set to the option target price '
                                    f'(${r["exit_price"]:.2f}) due to a bug where the position monitor '
                                    'compared stock prices against option-level targets. '
                                    'This trade\'s P&L is inaccurate. Bug has been fixed going forward.')
                note = (r['notes'] or '') + (' | ' if r['notes'] else '') + \
                       f'⚠️ DATA BUG: exit_price ${r["exit_price"]:.2f} was option target, not actual price.'
                conn.execute(
                    "UPDATE trades SET metadata=?, notes=? WHERE id=?",
                    (_json.dumps(meta), note, r['id'])
                )
            print(f"[Migration] Done — {len(rows)} record(s) flagged. "
                  "P&L for these trades is approximate.", flush=True)
    except Exception as e:
        print(f"[Migration] Warning: {e}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',       type=int, default=8080)
    parser.add_argument('--demo',       action='store_true')
    parser.add_argument('--scan-every', type=int, default=300)
    args = parser.parse_args()

    use_demo = args.demo or not broker.connected

    # Ensure users.db exists with default users (sam / hojr / bot)
    _ensure_default_users()

    # Pre-load all known user portfolios from disk
    _init_portfolios()

    # Fix any corrupt trade records from the old position-monitor bug
    _migrate_corrupt_trades()

    sam_port = _get_portfolio('sam')
    print(f"\n{'='*60}")
    print(f"  Options Trading Dashboard  (Fast Mode)")
    print(f"  Mode:      {'DEMO' if use_demo else broker.mode}")
    print(f"  Portfolio: {sam_port.db_path}")
    print(f"  Data dir:  {_data_dir()}")
    print(f"{'='*60}")
    print(f"\n  Open → http://localhost:{args.port}")
    print(f"  Scan starts in background — page loads instantly\n")

    # Scanner (background — page is served immediately without waiting)
    threading.Thread(target=_scanner_thread,
                     args=(use_demo, args.scan_every), daemon=True).start()

    # Live price loop (SSE push every 2s)
    threading.Thread(target=_price_loop, args=(use_demo,), daemon=True).start()

    # Position monitor (trigger check every 5 s)
    threading.Thread(target=_position_updater, daemon=True).start()

    # Refresh option quotes for open positions every 30 s
    threading.Thread(target=_refresh_position_opt_prices, daemon=True).start()

    # News engine (fetches immediately, then every 5 min)
    threading.Thread(target=_news_thread, daemon=True).start()

    app.run(host='0.0.0.0', port=args.port, debug=False, threaded=True)


if __name__ == '__main__':
    main()
