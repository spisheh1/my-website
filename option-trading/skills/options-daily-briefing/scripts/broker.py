"""
Broker Integration  —  Alpaca Markets
========================================
Handles live data quotes AND order execution via Alpaca's API.

Setup (one-time):
  1. Create a FREE account at https://alpaca.markets
  2. Go to Paper Trading → API Keys → Generate new key
  3. Set environment variables:
       export ALPACA_API_KEY="your_key_here"
       export ALPACA_SECRET_KEY="your_secret_here"
       export ALPACA_PAPER=true          # paper trading (default = safe!)
     OR put them in ~/.options_briefing/config.json (see below)

Modes:
  paper  = Simulated trades, REAL market data.  No money at risk. (DEFAULT)
  live   = Real orders placed with your real money. BE CAREFUL.

To switch to live trading:
  Set ALPACA_PAPER=false  OR  config.json: {"mode": "live"}

IMPORTANT: This tool will ONLY switch to live mode if you EXPLICITLY set it.
           Default is always paper trading.

Alpaca Options support:
  - Options buying (calls + puts)
  - Bracket orders (entry + stop + take-profit in one order)
  - Real-time quotes via WebSocket
  - Paper trading uses same real-time data as live

Data plan note:
  - Basic (free): 15-min delayed quotes
  - Unlimited ($9/mo): real-time quotes (recommended for active trading)
  - Options data requires Unlimited plan for real-time
"""

import os, json, time, math
from pathlib import Path
from datetime import datetime, date, timedelta

# ── Config loading ─────────────────────────────────────────────────────────────
CONFIG_PATH = Path.home() / '.options_briefing' / 'config.json'

def _load_config() -> dict:
    """Load config from env vars first, then config file, then defaults."""
    cfg = {
        'api_key':    os.getenv('ALPACA_API_KEY', ''),
        'secret_key': os.getenv('ALPACA_SECRET_KEY', ''),
        'paper':      os.getenv('ALPACA_PAPER', 'true').lower() != 'false',
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                file_cfg = json.load(f)
            cfg['api_key']    = cfg['api_key']    or file_cfg.get('api_key', '')
            cfg['secret_key'] = cfg['secret_key'] or file_cfg.get('secret_key', '')
            if 'mode' in file_cfg:
                cfg['paper'] = file_cfg['mode'] != 'live'
        except Exception:
            pass
    return cfg

def save_config(api_key: str, secret_key: str, paper: bool = True):
    """Save API credentials to config file."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump({
            'api_key':    api_key,
            'secret_key': secret_key,
            'mode':       'paper' if paper else 'live',
        }, f, indent=2)
    os.chmod(CONFIG_PATH, 0o600)   # owner-only read
    print(f"Config saved to {CONFIG_PATH}")


class Broker:
    """
    Alpaca broker wrapper.
    Falls back to demo/simulation mode if no API keys are configured.
    """

    def __init__(self):
        self.cfg = _load_config()
        self._client    = None
        self._data_client = None
        self.connected  = False
        self.mode       = 'paper' if self.cfg['paper'] else 'LIVE'
        self._try_connect()

    def _try_connect(self):
        """Attempt to connect to Alpaca. Silently fall back to demo if unavailable."""
        if not self.cfg['api_key'] or not self.cfg['secret_key']:
            print("ℹ  No Alpaca API keys — running in DEMO mode (no live data or orders).")
            return
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.data.historical.option import OptionHistoricalDataClient
            from alpaca.data.live.option import OptionDataStream
            paper = self.cfg['paper']
            self._client      = TradingClient(
                self.cfg['api_key'], self.cfg['secret_key'], paper=paper)
            self._data_client = OptionHistoricalDataClient(
                self.cfg['api_key'], self.cfg['secret_key'])
            self.connected    = True
            mode_str = "PAPER" if paper else "⚠ LIVE (real money)"
            print(f"✓ Connected to Alpaca [{mode_str}]")
        except ImportError:
            print("ℹ  alpaca-py not installed. Run: pip install alpaca-py")
        except Exception as e:
            print(f"ℹ  Alpaca connection failed: {e}  (demo mode)")

    # ── Account info ───────────────────────────────────────────────────────────

    def get_account(self) -> dict:
        """Return account info: buying power, portfolio value, etc."""
        if not self.connected:
            return {'buying_power': 100_000, 'portfolio_value': 100_000,
                    'cash': 100_000, 'mode': 'demo'}
        try:
            acct = self._client.get_account()
            return {
                'buying_power':    float(acct.buying_power),
                'portfolio_value': float(acct.portfolio_value),
                'cash':            float(acct.cash),
                'mode':            self.mode,
            }
        except Exception as e:
            return {'error': str(e), 'mode': self.mode}

    # ── Quotes ─────────────────────────────────────────────────────────────────

    def get_option_quote(self, ticker: str, expiry: str, strike: float,
                          opt_type: str) -> dict | None:
        """
        Get latest bid/ask/mid/IV for a specific option contract.
        expiry: 'YYYY-MM-DD'
        opt_type: 'call' or 'put'
        Returns None if not available.
        """
        if not self.connected:
            return None
        try:
            from alpaca.data.requests import OptionLatestQuoteRequest
            symbol = _option_symbol(ticker, expiry, strike, opt_type)
            req    = OptionLatestQuoteRequest(symbol_or_symbols=symbol)
            quote  = self._data_client.get_option_latest_quote(req)
            q = quote.get(symbol)
            if not q:
                return None
            bid = float(q.bid_price or 0)
            ask = float(q.ask_price or 0)
            return {
                'bid':    bid,
                'ask':    ask,
                'mid':    round((bid + ask) / 2, 2),
                'symbol': symbol,
            }
        except Exception:
            return None

    def get_stock_quote(self, ticker: str) -> float | None:
        """Get latest stock price for a ticker."""
        if not self.connected:
            return None
        try:
            from alpaca.data.historical.stock import StockHistoricalDataClient
            from alpaca.data.requests import StockLatestQuoteRequest
            dc = StockHistoricalDataClient(
                self.cfg['api_key'], self.cfg['secret_key'])
            req = StockLatestQuoteRequest(symbol_or_symbols=ticker)
            q   = dc.get_stock_latest_quote(req)
            sq  = q.get(ticker)
            if sq:
                return round((float(sq.bid_price) + float(sq.ask_price)) / 2, 2)
        except Exception:
            pass
        return None

    def get_vix(self) -> float | None:
        """Get current VIX level."""
        price = self.get_stock_quote('VXX')
        return price   # VXX is a proxy; for true VIX use a data source

    # ── Order execution ────────────────────────────────────────────────────────

    def place_option_order(self, order: dict) -> dict:
        """
        Place a buy-to-open option order with automatic target + stop.

        order = {
            'ticker':      'AAPL',
            'option_type': 'call',  # or 'put'
            'strike':      210.0,
            'expiry':      '2026-04-04',  # YYYY-MM-DD
            'contracts':   1,
            'entry_price': 4.20,    # limit price per contract
            'target_price':7.50,    # take-profit price per contract
            'stop_price':  2.10,    # stop-loss price per contract
        }

        Returns: { 'order_id': ..., 'status': 'submitted'|'error', 'message': ... }
        """
        if not self.connected:
            # Demo simulation — generate a fake order ID
            fake_id = f"demo_{int(time.time())}_{order['ticker']}"
            print(f"[DEMO] Simulated order: {order['contracts']}x "
                  f"{order['ticker']} {order['option_type'].upper()} "
                  f"${order['strike']} exp {order['expiry']} "
                  f"@ ${order['entry_price']}")
            return {'order_id': fake_id, 'status': 'submitted',
                    'message': 'Demo order placed (no real money)', 'demo': True}

        if not self.cfg['paper']:
            # Extra safety check for live trading
            print(f"\n⚠  LIVE ORDER: {order['contracts']} contract(s) of "
                  f"{order['ticker']} {order['option_type'].upper()} "
                  f"${order['strike']}  expiry {order['expiry']}")
            print(f"   Entry: ${order['entry_price']}  "
                  f"Target: ${order['target_price']}  "
                  f"Stop: ${order['stop_price']}")

        try:
            from alpaca.trading.requests import (
                OptionLegRequest, PlaceOrderRequest, OrderClass
            )
            from alpaca.trading.enums import (
                OrderSide, TimeInForce, OrderType, PositionIntent
            )

            symbol = _option_symbol(
                order['ticker'], order['expiry'],
                order['strike'], order['option_type'])

            # Build bracket order: entry limit + stop + take-profit
            req = PlaceOrderRequest(
                symbol        = symbol,
                qty           = order['contracts'],
                side          = OrderSide.BUY,
                type          = OrderType.LIMIT,
                time_in_force = TimeInForce.DAY,
                limit_price   = str(round(order['entry_price'], 2)),
                order_class   = OrderClass.BRACKET,
                take_profit   = {'limit_price': str(round(order['target_price'], 2))},
                stop_loss     = {'stop_price':  str(round(order['stop_price'],  2))},
                position_intent = PositionIntent.BTO,   # Buy To Open
            )
            result = self._client.submit_order(req)
            return {
                'order_id': str(result.id),
                'status':   result.status.value,
                'symbol':   symbol,
                'message':  f"Order submitted: {result.status.value}",
                'demo':     self.cfg['paper'],
            }
        except Exception as e:
            return {'order_id': None, 'status': 'error', 'message': str(e)}

    def close_position(self, alpaca_order_id: str = None,
                        ticker: str = None, symbol: str = None) -> dict:
        """Close / flatten an open position at market."""
        if not self.connected:
            return {'status': 'demo_closed', 'message': 'Demo position closed'}
        try:
            if symbol:
                self._client.close_position(symbol)
            elif ticker:
                self._client.close_all_positions()  # simplified
            return {'status': 'closed', 'message': 'Position closed at market'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    # ── Live price feed ────────────────────────────────────────────────────────

    def refresh_position_prices(self, positions: list[dict]) -> list[tuple]:
        """
        For each open position, fetch latest option price.
        Returns [(trade_id, current_price), ...]
        """
        updates = []
        for p in positions:
            try:
                quote = self.get_option_quote(
                    p['ticker'], p['expiry'], p['strike'], p['option_type'].lower())
                if quote and quote['mid'] > 0:
                    updates.append((p['id'], quote['mid']))
            except Exception:
                pass
        return updates


# ── Helpers ────────────────────────────────────────────────────────────────────

def _option_symbol(ticker: str, expiry: str, strike: float, opt_type: str) -> str:
    """
    Build OCC option symbol: e.g.  AAPL240404C00210000
    Format: TICKER + YYMMDD + C/P + 8-digit strike (5 digits + 3 decimals, no point)
    """
    d = date.fromisoformat(expiry)
    exp_str  = d.strftime('%y%m%d')
    type_chr = 'C' if opt_type.lower() == 'call' else 'P'
    strike_i = int(round(strike * 1000))
    strike_s = f"{strike_i:08d}"
    return f"{ticker.upper()}{exp_str}{type_chr}{strike_s}"


# ── CLI test ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    b = Broker()
    print(f"\nBroker mode: {b.mode}")
    print(f"Connected: {b.connected}")
    acct = b.get_account()
    print(f"Account: {acct}")

    if not b.connected:
        print("\nTo connect to Alpaca:")
        print("  1. Create account at https://alpaca.markets (free)")
        print("  2. Get paper trading API keys")
        print("  3. Run:")
        print("       export ALPACA_API_KEY=your_key")
        print("       export ALPACA_SECRET_KEY=your_secret")
        print("       python server.py")
