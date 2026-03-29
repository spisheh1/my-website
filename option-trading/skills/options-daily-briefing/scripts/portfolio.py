"""
Persistent Portfolio Tracker
==============================
ALL data stored at: ~/.options_briefing/portfolio.db

CRITICAL: This file lives in your HOME directory, completely separate
from the app. App updates will NEVER touch it. Back it up by copying:
  cp ~/.options_briefing/portfolio.db ~/Desktop/portfolio_backup.db

Tracks:
  - Every trade placed (open + closed)
  - Unrealized P&L for open positions (updated from live prices)
  - Realized P&L for closed trades
  - Overall stats: win rate, profit factor, total return
"""

import sqlite3, json, os
from datetime import datetime
from pathlib import Path

# ── Storage location — NEVER inside the app folder ────────────────────────────
PORTFOLIO_DIR = Path.home() / '.options_briefing'
DB_PATH       = PORTFOLIO_DIR / 'portfolio.db'

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT    NOT NULL,
    option_type     TEXT    NOT NULL,   -- CALL / PUT
    strike          REAL    NOT NULL,
    expiry          TEXT    NOT NULL,
    dte_at_entry    INTEGER NOT NULL,
    contracts       INTEGER NOT NULL DEFAULT 1,
    entry_price     REAL    NOT NULL,   -- per-contract option price
    target_price    REAL    NOT NULL,
    stop_price      REAL    NOT NULL,
    stock_price_at_entry REAL,
    iv_at_entry     REAL,
    delta_at_entry  REAL,
    score           REAL,
    timeframe       TEXT,
    mode            TEXT    NOT NULL DEFAULT 'paper',  -- paper / live
    status          TEXT    NOT NULL DEFAULT 'open',   -- open / closed / expired
    current_price   REAL,
    exit_price      REAL,
    exit_reason     TEXT,   -- target_hit / stop_hit / manual / expired
    opened_at       TEXT    NOT NULL,
    closed_at       TEXT,
    alpaca_order_id TEXT,
    notes           TEXT,
    metadata        TEXT    -- JSON blob for extras
);

CREATE TABLE IF NOT EXISTS price_updates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id    INTEGER NOT NULL REFERENCES trades(id),
    price       REAL    NOT NULL,
    updated_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);
"""

# ─────────────────────────────────────────────────────────────────────────────

class Portfolio:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")   # safe concurrent writes
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    # ── Trade lifecycle ────────────────────────────────────────────────────────

    def record_trade(self, trade: dict) -> int:
        """
        Record a new trade (just opened).
        Returns the trade ID.
        """
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            cur = conn.execute("""
                INSERT INTO trades (
                    ticker, option_type, strike, expiry, dte_at_entry,
                    contracts, entry_price, target_price, stop_price,
                    stock_price_at_entry, iv_at_entry, delta_at_entry,
                    score, timeframe, mode, status, current_price,
                    opened_at, alpaca_order_id, notes, metadata
                ) VALUES (
                    :ticker, :option_type, :strike, :expiry, :dte_at_entry,
                    :contracts, :entry_price, :target_price, :stop_price,
                    :stock_price, :iv, :delta,
                    :score, :timeframe, :mode, 'open', :entry_price,
                    :opened_at, :alpaca_order_id, :notes, :metadata
                )
            """, {
                'ticker':          trade['ticker'],
                'option_type':     trade['option_type'],
                'strike':          trade['strike'],
                'expiry':          trade['expiry'],
                'dte_at_entry':    trade['dte'],
                'contracts':       trade.get('contracts', 1),
                'entry_price':     trade['entry_price'],
                'target_price':    trade['target_price'],
                'stop_price':      trade['stop_price'],
                'stock_price':     trade.get('stock_price'),
                'iv':              trade.get('iv'),
                'delta':           trade.get('delta'),
                'score':           trade.get('score'),
                'timeframe':       trade.get('timeframe'),
                'mode':            trade.get('mode', 'paper'),
                'opened_at':       now,
                'alpaca_order_id': trade.get('alpaca_order_id'),
                'notes':           trade.get('notes', ''),
                'metadata':        json.dumps(trade.get('metadata', {})),
            })
            return cur.lastrowid

    def update_price(self, trade_id: int, current_price: float):
        """Update current market price for an open position."""
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE trades SET current_price=? WHERE id=? AND status='open'",
                (current_price, trade_id))
            conn.execute(
                "INSERT INTO price_updates (trade_id, price, updated_at) VALUES (?,?,?)",
                (trade_id, current_price, now))

    def close_trade(self, trade_id: int, exit_price: float, reason: str):
        """Mark a trade as closed."""
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute("""
                UPDATE trades SET
                    status='closed', exit_price=?, exit_reason=?,
                    current_price=?, closed_at=?
                WHERE id=?
            """, (exit_price, reason, exit_price, now, trade_id))

    def update_prices_bulk(self, updates: list[tuple]):
        """Updates = [(trade_id, price), ...]"""
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            for trade_id, price in updates:
                conn.execute(
                    "UPDATE trades SET current_price=? WHERE id=? AND status='open'",
                    (price, trade_id))
                conn.execute(
                    "INSERT INTO price_updates (trade_id, price, updated_at) VALUES (?,?,?)",
                    (trade_id, price, now))

    # ── Queries ────────────────────────────────────────────────────────────────

    def get_open_positions(self) -> list[dict]:
        """Return all open positions as list of dicts."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM trades WHERE status='open'
                ORDER BY opened_at DESC
            """).fetchall()
            positions = []
            for r in rows:
                d = dict(r)
                cp = d.get('current_price') or d['entry_price']
                ep = d['entry_price']
                contracts = d.get('contracts', 1)
                cost_basis     = ep * 100 * contracts
                current_value  = cp * 100 * contracts
                unrealized_pnl = current_value - cost_basis
                unrealized_pct = unrealized_pnl / cost_basis * 100 if cost_basis else 0
                d['unrealized_pnl'] = round(unrealized_pnl, 2)
                d['unrealized_pct'] = round(unrealized_pct, 1)
                d['cost_basis']     = round(cost_basis, 2)
                d['current_value']  = round(current_value, 2)
                # pct to target
                if d['target_price'] > ep:
                    d['pct_to_target'] = round((d['target_price'] - cp) / (d['target_price'] - ep) * 100, 1)
                else:
                    d['pct_to_target'] = 0
                positions.append(d)
            return positions

    def get_closed_trades(self, limit: int = 100) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM trades WHERE status='closed'
                ORDER BY closed_at DESC LIMIT ?
            """, (limit,)).fetchall()
            trades = []
            for r in rows:
                d = dict(r)
                ep = d['entry_price']
                xp = d.get('exit_price') or ep
                contracts = d.get('contracts', 1)
                d['realized_pnl'] = round((xp - ep) * 100 * contracts, 2)
                d['realized_pct'] = round((xp - ep) / ep * 100, 1) if ep else 0
                trades.append(d)
            return trades

    def get_summary(self) -> dict:
        """Full portfolio summary — the "total gains and losses" view."""
        with self._conn() as conn:
            # Open positions
            open_rows = conn.execute(
                "SELECT * FROM trades WHERE status='open'").fetchall()
            # Closed trades
            closed_rows = conn.execute(
                "SELECT * FROM trades WHERE status='closed'").fetchall()

        unrealized_pnl = 0.0
        total_open_cost = 0.0
        for r in open_rows:
            d = dict(r)
            cp = d.get('current_price') or d['entry_price']
            ep = d['entry_price']
            c  = d.get('contracts', 1)
            unrealized_pnl  += (cp - ep) * 100 * c
            total_open_cost += ep * 100 * c

        realized_pnl = 0.0
        wins = 0
        losses = 0
        total_closed = len(closed_rows)
        gross_profit = 0.0
        gross_loss   = 0.0
        for r in closed_rows:
            d = dict(r)
            ep = d['entry_price']
            xp = d.get('exit_price') or ep
            c  = d.get('contracts', 1)
            pnl = (xp - ep) * 100 * c
            realized_pnl += pnl
            if pnl > 0:
                wins += 1
                gross_profit += pnl
            else:
                losses += 1
                gross_loss   += abs(pnl)

        win_rate      = wins / total_closed * 100 if total_closed else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        total_pnl     = unrealized_pnl + realized_pnl

        return {
            'total_pnl':        round(total_pnl, 2),
            'unrealized_pnl':   round(unrealized_pnl, 2),
            'realized_pnl':     round(realized_pnl, 2),
            'total_open_cost':  round(total_open_cost, 2),
            'open_positions':   len(open_rows),
            'closed_trades':    total_closed,
            'wins':             wins,
            'losses':           losses,
            'win_rate':         round(win_rate, 1),
            'profit_factor':    round(profit_factor, 2) if profit_factor != float('inf') else 999,
            'gross_profit':     round(gross_profit, 2),
            'gross_loss':       round(gross_loss, 2),
        }

    def get_setting(self, key: str, default=None):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row['value'] if row else default

    def set_setting(self, key: str, value: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)",
                (key, str(value)))

    def export_to_json(self, path: str = None) -> str:
        """Export full portfolio history to JSON (for backup)."""
        path = path or str(PORTFOLIO_DIR / 'portfolio_export.json')
        data = {
            'exported_at':  datetime.utcnow().isoformat(),
            'summary':      self.get_summary(),
            'open':         self.get_open_positions(),
            'closed':       self.get_closed_trades(limit=10000),
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        return path


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    p = Portfolio()
    s = p.get_summary()
    print(f"\nPortfolio Summary  ({DB_PATH})")
    print(f"{'='*50}")
    print(f"  Total P&L:      ${s['total_pnl']:>10,.2f}")
    print(f"  Unrealized:     ${s['unrealized_pnl']:>10,.2f}")
    print(f"  Realized:       ${s['realized_pnl']:>10,.2f}")
    print(f"  Open positions: {s['open_positions']}")
    print(f"  Closed trades:  {s['closed_trades']}  (W:{s['wins']} / L:{s['losses']})")
    print(f"  Win rate:       {s['win_rate']}%")
    print(f"  Profit factor:  {s['profit_factor']}")
    print(f"\n  DB location:    {DB_PATH}")
    print(f"  Backup command: cp {DB_PATH} ~/portfolio_backup.db\n")
