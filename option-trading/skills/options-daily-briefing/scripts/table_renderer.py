"""
Compact Table Dashboard Renderer  (with expandable detail panels)
===================================================================
Each table row is clickable — expands into a full reasoning panel:
  • Trade setup summary
  • Technical analysis (RSI, MACD, SMA, Bollinger Bands, ATR)
  • Options logic (strike selection, theta decay, vega risk)
  • Probability breakdown (P(touch), P(ITM), breakeven)
  • Risk management (sizing, stop, target rules, red flags)
  • Step-by-step execution checklist
"""

import json
from screener import TIMEFRAMES

# ─── Colour palette ────────────────────────────────────────────────────────────
BG       = '#0d1117'
SURFACE  = '#161b22'
SURFACE2 = '#21262d'
SURFACE3 = '#2d333b'
BORDER   = '#30363d'
TEXT     = '#e6edf3'
TEXT2    = '#8b949e'
TEXT3    = '#6e7681'
GREEN    = '#3fb950'
RED      = '#f85149'
YELLOW   = '#d29922'
BLUE     = '#58a6ff'
PURPLE   = '#bc8cff'
ORANGE   = '#ffa657'
TEAL     = '#39d353'
PINK     = '#ff7b72'

# ─── Small helpers ─────────────────────────────────────────────────────────────

def _badge(text, color):
    return (f'<span style="background:{color}22;color:{color};border:1px solid {color}44;'
            f'border-radius:4px;padding:1px 8px;font-size:11px;font-weight:700;">{text}</span>')

def _type_badge(opt_type):
    return _badge(opt_type, GREEN if opt_type == 'CALL' else RED)

def _score_badge(score):
    col = GREEN if score >= 75 else (YELLOW if score >= 55 else TEXT2)
    return f'<span style="color:{col};font-weight:800;font-size:16px;">{score:.0f}</span><span style="color:{TEXT3};font-size:11px;">/100</span>'

def _trend_icon(trend):
    t = trend.lower()
    if t == 'bullish': return f'<span style="color:{GREEN}">▲ Bull</span>'
    if t == 'bearish': return f'<span style="color:{RED}">▼ Bear</span>'
    return f'<span style="color:{YELLOW}">◆ Side</span>'

def _pct_bar(val, color=TEAL, width=90):
    w = min(100, max(0, val))
    return (f'<div style="display:inline-flex;align-items:center;gap:6px;">'
            f'<div style="background:{BORDER};border-radius:3px;height:7px;width:{width}px;">'
            f'<div style="background:{color};width:{w:.0f}%;height:100%;border-radius:3px;'
            f'transition:width 0.3s;"></div></div>'
            f'<span style="color:{color};font-weight:600;font-size:12px;">{val:.0f}%</span>'
            f'</div>')

def _kv(label, value, color=TEXT, note=''):
    note_html = f'<span style="color:{TEXT3};font-size:11px;margin-left:6px;">{note}</span>' if note else ''
    return (f'<div style="margin-bottom:4px;">'
            f'<span style="color:{TEXT2};font-size:11px;min-width:110px;display:inline-block;">{label}</span>'
            f'<span style="color:{color};font-weight:600;">{value}</span>{note_html}</div>')

def _section_title(title, color=BLUE):
    return (f'<div style="color:{color};font-size:12px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:1px;border-bottom:1px solid {color}33;padding-bottom:6px;'
            f'margin:18px 0 10px;">{title}</div>')

def _risk_tag(text):
    return (f'<div style="background:#3d1a1a;color:{RED};border-left:3px solid {RED};'
            f'padding:6px 10px;border-radius:0 4px 4px 0;font-size:12px;margin-bottom:6px;">'
            f'⚠ {text}</div>')

def _check_item(text):
    return (f'<div style="display:flex;gap:8px;align-items:flex-start;margin-bottom:8px;">'
            f'<span style="color:{GREEN};font-size:14px;margin-top:1px;">☐</span>'
            f'<span style="color:{TEXT};font-size:13px;">{text}</span></div>')

def _info_card(label, value, sub='', color=TEXT):
    return (f'<div style="background:{SURFACE3};border:1px solid {BORDER};border-radius:8px;'
            f'padding:12px 16px;min-width:120px;flex:1;">'
            f'<div style="color:{TEXT2};font-size:11px;text-transform:uppercase;letter-spacing:0.5px;">{label}</div>'
            f'<div style="color:{color};font-size:20px;font-weight:800;margin:4px 0;">{value}</div>'
            f'<div style="color:{TEXT3};font-size:11px;">{sub}</div></div>')

def _greek_card(label, value, meaning, color):
    return (f'<div style="background:{SURFACE3};border:1px solid {BORDER};border-radius:8px;'
            f'padding:12px;flex:1;min-width:100px;">'
            f'<div style="color:{TEXT2};font-size:11px;text-transform:uppercase;letter-spacing:0.5px;">{label}</div>'
            f'<div style="color:{color};font-size:18px;font-weight:800;margin:4px 0;">{value}</div>'
            f'<div style="color:{TEXT3};font-size:11px;">{meaning}</div></div>')

# ─── Detail panel HTML ─────────────────────────────────────────────────────────

def _detail_panel(c):
    """Full expandable detail panel for one candidate."""
    r = c.get('reasoning', {})
    setup    = r.get('setup', {})
    tech     = r.get('technicals', {})
    optlogic = r.get('option_logic', {})
    probs    = r.get('probabilities', {})
    risk_mgmt = r.get('risk_management', {})
    checklist = r.get('execution', [])
    is_call  = c['option_type'] == 'CALL'
    type_color = GREEN if is_call else RED
    score_color = GREEN if c['score'] >= 75 else (YELLOW if c['score'] >= 55 else TEXT2)

    # ── Top summary bar ──────────────────────────────────────────────
    headline = setup.get('headline', f"{c['ticker']} {c['option_type']}")
    summary = f"""
    <div style="background:{SURFACE3};border-radius:8px;padding:16px 20px;margin-bottom:20px;
                border-left:4px solid {type_color};">
      <div style="font-size:15px;font-weight:700;color:{TEXT};margin-bottom:8px;">{headline}</div>
      <div style="display:flex;flex-wrap:wrap;gap:10px;">
        {_info_card('Entry', f'${c["entry"]:.2f}', f'{c["dte"]} DTE option', ORANGE)}
        {_info_card('Target', f'${c["target"]:.2f}', f'+{round((c["target"]-c["entry"])/c["entry"]*100,0):.0f}% gain', GREEN)}
        {_info_card('Stop', f'${c["stop"]:.2f}', f'-{round((c["entry"]-c["stop"])/c["entry"]*100,0):.0f}% loss', RED)}
        {_info_card('R:R', f'{c["rr"]:.1f}x', 'reward per $1 risked', PURPLE)}
        {_info_card('Score', f'{c["score"]:.0f}/100', 'conviction level', score_color)}
        {_info_card('P(Hit)', f'{c["p_touch"]:.0f}%', 'touches target before expiry', TEAL)}
      </div>
    </div>"""

    # ── Greeks row ───────────────────────────────────────────────────
    greeks_section = f"""
    {_section_title('Greeks Explained', PURPLE)}
    <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:6px;">
      {_greek_card('Delta', f'{c["delta"]:.2f}',
                   f'Moves ${c["delta"]:.2f} per $1 in {c["ticker"]}', BLUE)}
      {_greek_card('Theta', f'{c["theta"]:.3f}',
                   f'Loses ${abs(c["theta"]):.3f}/day to decay', RED)}
      {_greek_card('Vega', f'{c["vega"]:.3f}',
                   f'${c["vega"]:.3f} per 1% IV change', YELLOW)}
      {_greek_card('Gamma', f'{c.get("gamma", 0):.5f}',
                   'Rate of delta change', TEAL)}
      {_greek_card('IV%', f'{c["iv_pct"]:.0f}%',
                   f'IVR: {c["iv_rank"]:.0f} ({"cheap" if c["iv_rank"] < 40 else "fair" if c["iv_rank"] < 65 else "expensive"})', ORANGE)}
    </div>
    <p style="color:{TEXT2};font-size:12px;margin-top:8px;">
      {optlogic.get('theta', '')}
    </p>
    <p style="color:{TEXT2};font-size:12px;margin-top:6px;">
      {optlogic.get('vega', '')}
    </p>"""

    # ── Setup section ────────────────────────────────────────────────
    setup_section = f"""
    {_section_title('Market Setup & Thesis', BLUE)}
    <p style="color:{TEXT};font-size:13px;line-height:1.7;margin-bottom:10px;">
      {setup.get('trend', '')}
    </p>
    <p style="color:{TEXT};font-size:13px;line-height:1.7;margin-bottom:10px;">
      {setup.get('iv', '')}
    </p>
    <p style="color:{TEXT2};font-size:13px;line-height:1.7;">
      {setup.get('em', '')}
    </p>"""

    # ── Technicals section ───────────────────────────────────────────
    sma_bars = ''
    for label, val, color in [
        ('SMA 20',  c.get('sma20',  c['price']), BLUE),
        ('SMA 50',  c.get('sma50',  c['price']), ORANGE),
        ('SMA 200', c.get('sma200', c['price']), PURPLE),
    ]:
        diff = round((c['price'] - val) / val * 100, 1)
        sign = '+' if diff >= 0 else ''
        sig  = GREEN if diff >= 0 else RED
        sma_bars += (f'<div style="display:flex;justify-content:space-between;align-items:center;'
                     f'padding:5px 0;border-bottom:1px solid {BORDER};">'
                     f'<span style="color:{color};font-size:12px;min-width:70px;">{label}</span>'
                     f'<span style="color:{TEXT};font-size:13px;">${val:.2f}</span>'
                     f'<span style="color:{sig};font-size:12px;">{sign}{diff}% vs price</span></div>')

    tech_section = f"""
    {_section_title('Technical Analysis', ORANGE)}
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
      <div>
        <div style="color:{TEXT2};font-size:11px;text-transform:uppercase;
                    letter-spacing:0.5px;margin-bottom:8px;">Momentum</div>
        {_kv('RSI (14)', f'{c["rsi"]:.1f}',
             GREEN if 40 <= c["rsi"] <= 60 else (RED if c["rsi"] > 70 or c["rsi"] < 30 else YELLOW),
             'overbought' if c["rsi"] > 70 else ('oversold' if c["rsi"] < 30 else 'neutral'))}
        {_kv('MACD', f'{c.get("macd_val", 0):.4f}', BLUE)}
        {_kv('Signal', f'{c.get("macd_sig", 0):.4f}', BLUE)}
        {_kv('ATR (14)', f'${c.get("atr", 0):.2f}', TEXT,
             f'({round(c.get("atr",0)/c["price"]*100,1)}% daily range)')}
        <p style="color:{TEXT2};font-size:12px;margin-top:8px;line-height:1.6;">
          {tech.get('rsi', '')}
        </p>
        <p style="color:{TEXT2};font-size:12px;margin-top:6px;line-height:1.6;">
          {tech.get('macd', '')}
        </p>
      </div>
      <div>
        <div style="color:{TEXT2};font-size:11px;text-transform:uppercase;
                    letter-spacing:0.5px;margin-bottom:8px;">Moving Averages vs Price ${c["price"]:.2f}</div>
        {sma_bars}
        <div style="margin-top:10px;color:{TEXT2};font-size:11px;text-transform:uppercase;
                    letter-spacing:0.5px;margin-bottom:6px;">Bollinger Bands</div>
        {_kv('Upper', f'${c.get("bb_upper", c["price"]*1.02):.2f}', RED)}
        {_kv('Middle', f'${c.get("bb_mid", c["price"]):.2f}', TEXT)}
        {_kv('Lower', f'${c.get("bb_lower", c["price"]*0.98):.2f}', GREEN)}
        <p style="color:{TEXT2};font-size:12px;margin-top:8px;line-height:1.6;">
          {tech.get('bb', '')}
        </p>
      </div>
    </div>"""

    # ── Options logic section ────────────────────────────────────────
    options_section = f"""
    {_section_title('Options Logic', TEAL)}
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
      <div>
        {_kv('Strike', f'${c["strike"]:.2f}', TEXT)}
        {_kv('Expiry', c["expiry"], TEXT)}
        {_kv('DTE', str(c["dte"]) + ' days', TEXT)}
        {_kv('Breakeven', f'${c["breakeven"]:.2f}', YELLOW,
             f'({round(abs(c["breakeven"]-c["price"])/c["price"]*100,1)}% move needed)')}
        {_kv('Stock Target', f'${c.get("price_target_stock", c["stock_target"]):.2f}', GREEN)}
        {_kv('Stock Stop', f'${c.get("stop_loss_stock", 0):.2f}', RED)}
      </div>
      <div>
        <p style="color:{TEXT2};font-size:12px;line-height:1.6;margin-bottom:10px;">
          {optlogic.get('strike', '')}
        </p>
        <p style="color:{TEXT2};font-size:12px;line-height:1.6;">
          {optlogic.get('timing', '')}
        </p>
      </div>
    </div>"""

    # ── Probabilities section ────────────────────────────────────────
    prob_section = f"""
    {_section_title('Probability Analysis', PINK)}
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:12px;">
      <div>
        <div style="color:{TEXT2};font-size:11px;margin-bottom:6px;">Prob. of touching target before expiry</div>
        {_pct_bar(c['p_touch'], TEAL, 150)}
        <p style="color:{TEXT2};font-size:12px;margin-top:8px;line-height:1.6;">
          {probs.get('p_touch', '')}
        </p>
      </div>
      <div>
        <div style="color:{TEXT2};font-size:11px;margin-bottom:6px;">Prob. of expiring in-the-money</div>
        {_pct_bar(c['p_profit'], BLUE, 150)}
        <p style="color:{TEXT2};font-size:12px;margin-top:8px;line-height:1.6;">
          {probs.get('p_profit', '')}
        </p>
      </div>
    </div>
    <div style="background:{SURFACE3};border-radius:6px;padding:12px;margin-top:8px;">
      <p style="color:{TEXT};font-size:13px;line-height:1.6;margin-bottom:6px;">
        <strong>Breakeven:</strong> {probs.get('breakeven', '')}
      </p>
      <p style="color:{TEXT};font-size:13px;line-height:1.6;">
        <strong>Risk/Reward:</strong> {probs.get('rr', '')}
      </p>
    </div>"""

    # ── Risk management section ──────────────────────────────────────
    risk_tags = ''.join(_risk_tag(r) for r in risk_mgmt.get('risks', []))
    risk_section = f"""
    {_section_title('Risk Management', RED)}
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:12px;">
      <div>
        <div style="color:{TEXT2};font-size:11px;text-transform:uppercase;
                    letter-spacing:0.5px;margin-bottom:8px;">Stop Rules</div>
        <p style="color:{TEXT};font-size:12px;line-height:1.6;">{risk_mgmt.get('stop', '')}</p>
        <div style="color:{TEXT2};font-size:11px;text-transform:uppercase;
                    letter-spacing:0.5px;margin:12px 0 8px;">Profit Taking</div>
        <p style="color:{TEXT};font-size:12px;line-height:1.6;">{risk_mgmt.get('target', '')}</p>
      </div>
      <div>
        <div style="color:{TEXT2};font-size:11px;text-transform:uppercase;
                    letter-spacing:0.5px;margin-bottom:8px;">Position Sizing</div>
        <p style="color:{TEXT};font-size:12px;line-height:1.6;">{risk_mgmt.get('sizing', '')}</p>
      </div>
    </div>
    <div style="color:{TEXT2};font-size:11px;text-transform:uppercase;
                letter-spacing:0.5px;margin-bottom:8px;">Risk Flags</div>
    {risk_tags}"""

    # ── Execution checklist ──────────────────────────────────────────
    checks = ''.join(_check_item(item) for item in checklist)
    exec_section = f"""
    {_section_title('Execution Checklist', GREEN)}
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;">
      {checks}
    </div>"""

    return f"""
    <div style="background:{SURFACE};border:1px solid {BORDER};border-radius:10px;
                padding:24px;margin:0 0 4px 0;">
      {summary}
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
        <div>{setup_section}{greeks_section}</div>
        <div>{tech_section}</div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:4px;">
        <div>{options_section}{prob_section}</div>
        <div>{risk_section}{exec_section}</div>
      </div>
    </div>"""


# ─── Table row + hidden detail row ────────────────────────────────────────────

def _row_with_detail(rank, c, uid):
    """Compact summary row + hidden detail row, toggled on click."""
    import json as _json
    bg, _ = (('#0d4a1e', GREEN) if c['score'] >= 75
             else (('#3b2800', YELLOW) if c['score'] >= 55
             else (SURFACE2, TEXT2)))
    # Payload for the invest modal — strip the large reasoning dict to keep HTML light
    invest_payload = {k: v for k, v in c.items() if k != 'reasoning'}
    invest_json = _json.dumps(invest_payload).replace("'", "&#39;").replace('"', '&quot;')
    entry  = c['entry']
    target = c['target']
    upside = round((target - entry) / entry * 100, 0) if entry else 0

    summary_row = f"""
    <tr class="pick-row" data-uid="{uid}" data-score="{c['score']}" data-ticker="{c['ticker']}"
        onclick="toggleDetail('{uid}')"
        style="background:{bg};border-bottom:1px solid {BORDER};cursor:pointer;">
      <td style="padding:11px 8px;text-align:center;color:{TEXT2};font-size:12px;">{rank}</td>
      <td style="padding:11px 8px;">
        <span style="color:{BLUE};font-weight:800;font-size:15px;">{c['ticker']}</span>
        <div style="color:{TEXT2};font-size:10px;">{c['sector']}</div>
      </td>
      <td style="padding:11px 8px;">{_type_badge(c['option_type'])}</td>
      <td style="padding:11px 8px;color:{TEXT};font-weight:600;">${c['strike']:.2f}</td>
      <td style="padding:11px 8px;">
        <span style="color:{TEXT};font-size:13px;">{c['expiry']}</span>
        <span style="color:{TEXT2};font-size:10px;margin-left:3px;">({c['dte']}d)</span>
      </td>
      <td style="padding:11px 8px;font-weight:700;color:{ORANGE};">${entry:.2f}</td>
      <td style="padding:11px 8px;">
        <span style="font-weight:700;color:{GREEN};">${target:.2f}</span>
        <span style="color:{TEXT2};font-size:10px;margin-left:3px;">(+{upside:.0f}%)</span>
      </td>
      <td style="padding:11px 8px;color:{RED};font-weight:600;">${c['stop']:.2f}</td>
      <td style="padding:11px 8px;color:{PURPLE};font-weight:600;">{c['rr']:.1f}x</td>
      <td style="padding:11px 8px;text-align:center;">{_score_badge(c['score'])}</td>
      <td style="padding:11px 8px;">{_pct_bar(c['p_touch'], TEAL, 70)}</td>
      <td style="padding:11px 8px;color:{TEXT2};">{c['iv_pct']:.0f}%</td>
      <td style="padding:11px 8px;">
        <span style="color:{'#F85149' if c['iv_rank'] > 60 else '#58a6ff'};">{c['iv_rank']:.0f}</span>
      </td>
      <td style="padding:11px 8px;color:{TEXT2};">{c['delta']:.2f}</td>
      <td style="padding:11px 8px;">{_trend_icon(c['trend'])}</td>
      <td style="padding:11px 8px;">
        <div style="color:{TEXT2};font-size:11px;">RSI {c['rsi']:.0f}</div>
        <div style="color:{TEXT2};font-size:11px;">θ {c['theta']:.3f}</div>
      </td>
      <td style="padding:11px 8px;text-align:center;">
        <span id="arrow-{uid}" style="color:{TEXT2};font-size:14px;">▼</span>
      </td>
      <td style="padding:8px;" onclick="event.stopPropagation();">
        <button onclick="openInvestModal({invest_json})"
                style="background:linear-gradient(135deg,{GREEN},{TEAL});color:#000;
                       border:none;border-radius:6px;padding:6px 14px;font-size:12px;
                       font-weight:800;cursor:pointer;letter-spacing:0.5px;
                       transition:opacity 0.15s;" onmouseover="this.style.opacity=0.8"
                onmouseout="this.style.opacity=1">
          INVEST
        </button>
      </td>
    </tr>
    <tr id="detail-{uid}" style="display:none;">
      <td colspan="17" style="padding:0 8px 12px;background:{BG};">
        {_detail_panel(c)}
      </td>
    </tr>"""

    return summary_row


# ─── Table section ────────────────────────────────────────────────────────────

def _table_section(tf_key, tf_info, candidates):
    label   = tf_info['label']
    desc    = tf_info['desc']
    n_picks = len(candidates)
    icon    = {'short': '⚡', 'mid': '📈', 'long': '🏔️'}.get(tf_key, '📊')
    header_color = {'short': ORANGE, 'mid': BLUE, 'long': PURPLE}.get(tf_key, BLUE)

    thead = f"""
    <tr style="background:{SURFACE2};border-bottom:2px solid {header_color};">
      <th style="padding:10px 8px;color:{TEXT2};font-size:11px;font-weight:600;">RANK</th>
      <th style="padding:10px 8px;color:{TEXT2};font-size:11px;cursor:pointer;" onclick="sortTable('{tf_key}',1)">TICKER ⇅</th>
      <th style="padding:10px 8px;color:{TEXT2};font-size:11px;">TYPE</th>
      <th style="padding:10px 8px;color:{TEXT2};font-size:11px;cursor:pointer;" onclick="sortTable('{tf_key}',3)">STRIKE ⇅</th>
      <th style="padding:10px 8px;color:{TEXT2};font-size:11px;">EXPIRY</th>
      <th style="padding:10px 8px;color:{ORANGE};font-size:11px;">ENTRY $</th>
      <th style="padding:10px 8px;color:{GREEN};font-size:11px;">TARGET $</th>
      <th style="padding:10px 8px;color:{RED};font-size:11px;">STOP $</th>
      <th style="padding:10px 8px;color:{PURPLE};font-size:11px;cursor:pointer;" onclick="sortTable('{tf_key}',8)">R:R ⇅</th>
      <th style="padding:10px 8px;color:{TEXT2};font-size:11px;cursor:pointer;" onclick="sortTable('{tf_key}',9)">SCORE ⇅</th>
      <th style="padding:10px 8px;color:{TEAL};font-size:11px;cursor:pointer;" onclick="sortTable('{tf_key}',10)">P(HIT) ⇅</th>
      <th style="padding:10px 8px;color:{TEXT2};font-size:11px;">IV%</th>
      <th style="padding:10px 8px;color:{TEXT2};font-size:11px;">IVR</th>
      <th style="padding:10px 8px;color:{TEXT2};font-size:11px;">DELTA</th>
      <th style="padding:10px 8px;color:{TEXT2};font-size:11px;">TREND</th>
      <th style="padding:10px 8px;color:{TEXT2};font-size:11px;">EXTRAS</th>
      <th style="padding:10px 8px;color:{TEXT2};font-size:11px;text-align:center;">↕</th>
      <th style="padding:10px 8px;color:{GREEN};font-size:11px;text-align:center;">ACTION</th>
    </tr>"""

    rows = ''
    for i, c in enumerate(candidates):
        uid = f"{tf_key}_{c['ticker']}_{i}"
        rows += _row_with_detail(i + 1, c, uid)

    return f"""
  <div style="margin-bottom:44px;" id="section-{tf_key}">
    <div style="display:flex;align-items:baseline;gap:12px;margin-bottom:12px;flex-wrap:wrap;">
      <h2 style="margin:0;color:{header_color};font-size:20px;">{icon} {label}</h2>
      <span style="color:{TEXT2};font-size:13px;">{desc} · {n_picks} picks · click any row for full analysis</span>
    </div>
    <div style="overflow-x:auto;border-radius:8px;border:1px solid {BORDER};">
      <table id="table-{tf_key}" style="width:100%;border-collapse:collapse;font-size:13px;
             font-family:'SF Mono',Consolas,monospace;min-width:1050px;">
        <thead>{thead}</thead>
        <tbody id="tbody-{tf_key}">{rows}</tbody>
      </table>
    </div>
  </div>"""


# ─── Market summary bar ───────────────────────────────────────────────────────

def _market_summary_bar(vix, date_str, regime_counts):
    bull  = regime_counts.get('Bullish', 0)
    bear  = regime_counts.get('Bearish', 0)
    side  = regime_counts.get('Sideways', 0)
    total = bull + bear + side or 1
    bias  = 'BULLISH' if bull > bear else ('BEARISH' if bear > bull else 'NEUTRAL')
    bc    = GREEN if bias == 'BULLISH' else (RED if bias == 'BEARISH' else YELLOW)
    vc    = GREEN if vix < 15 else (YELLOW if vix < 20 else (ORANGE if vix < 25 else RED))

    return f"""
  <div style="background:{SURFACE};border:1px solid {BORDER};border-radius:10px;
              padding:18px 28px;margin-bottom:32px;display:flex;flex-wrap:wrap;gap:28px;align-items:center;">
    <div>
      <div style="color:{TEXT2};font-size:10px;text-transform:uppercase;letter-spacing:1px;">Date</div>
      <div style="color:{TEXT};font-size:18px;font-weight:700;">{date_str}</div>
    </div>
    <div>
      <div style="color:{TEXT2};font-size:10px;text-transform:uppercase;letter-spacing:1px;">VIX</div>
      <div style="color:{vc};font-size:22px;font-weight:800;">{vix:.1f}
        <span style="font-size:12px;font-weight:400;color:{TEXT2};">
          {'— calm, cheap options' if vix < 15 else '— normal conditions' if vix < 20 else '— elevated fear' if vix < 25 else '— high fear / wide spreads'}
        </span>
      </div>
    </div>
    <div>
      <div style="color:{TEXT2};font-size:10px;text-transform:uppercase;letter-spacing:1px;">Market Bias</div>
      <div style="color:{bc};font-size:18px;font-weight:700;">{bias}</div>
    </div>
    <div>
      <div style="color:{TEXT2};font-size:10px;text-transform:uppercase;letter-spacing:1px;">Regime Split ({total} tickers)</div>
      <div style="display:flex;gap:14px;margin-top:4px;">
        <span style="color:{GREEN};font-weight:700;">{bull} Bull ({bull/total*100:.0f}%)</span>
        <span style="color:{YELLOW};font-weight:700;">{side} Side ({side/total*100:.0f}%)</span>
        <span style="color:{RED};font-weight:700;">{bear} Bear ({bear/total*100:.0f}%)</span>
      </div>
    </div>
    <div style="margin-left:auto;">
      <div style="color:{TEXT2};font-size:10px;margin-bottom:6px;">Score Legend</div>
      <div style="display:flex;gap:8px;">
        {_badge('75+ BUY FULL SIZE', GREEN)}
        {_badge('55+ WATCH / HALF SIZE', YELLOW)}
        {_badge('<55 SKIP', TEXT2)}
      </div>
    </div>
  </div>"""


# ─── JavaScript ───────────────────────────────────────────────────────────────

JS = """
<script>
function toggleDetail(uid) {
  const row   = document.getElementById('detail-' + uid);
  const arrow = document.getElementById('arrow-' + uid);
  const open  = row.style.display !== 'none';
  row.style.display   = open ? 'none' : 'table-row';
  arrow.textContent   = open ? '▼' : '▲';
  arrow.style.color   = open ? '#8b949e' : '#58a6ff';
}

function sortTable(tfKey, colIdx) {
  const tbody = document.getElementById('tbody-' + tfKey);
  // Collect only summary rows (even-indexed children, skip detail rows)
  const allRows = Array.from(tbody.children);
  const pairs = [];
  for (let i = 0; i < allRows.length; i += 2) {
    pairs.push([allRows[i], allRows[i+1]]);
  }
  const asc = tbody.dataset.sortCol == colIdx && tbody.dataset.sortDir == 'asc';
  tbody.dataset.sortCol = colIdx;
  tbody.dataset.sortDir = asc ? 'desc' : 'asc';
  pairs.sort((a, b) => {
    const av = a[0].cells[colIdx].textContent.replace(/[^0-9.\-]/g, '');
    const bv = b[0].cells[colIdx].textContent.replace(/[^0-9.\-]/g, '');
    const an = parseFloat(av) || av;
    const bn = parseFloat(bv) || bv;
    return asc ? (an < bn ? 1 : an > bn ? -1 : 0) : (an > bn ? 1 : an < bn ? -1 : 0);
  });
  pairs.forEach(([sumRow, detRow]) => {
    tbody.appendChild(sumRow);
    tbody.appendChild(detRow);
  });
}

function filterAll(val) {
  val = val.toLowerCase();
  document.querySelectorAll('.pick-row').forEach(r => {
    const ticker = r.dataset.ticker.toLowerCase();
    const show = !val || ticker.includes(val);
    r.style.display = show ? '' : 'none';
    // Also hide the detail row below it
    const uid = r.dataset.uid;
    const detRow = document.getElementById('detail-' + uid);
    if (detRow && !show) detRow.style.display = 'none';
  });
}
</script>
"""

# ─── Main render function ────────────────────────────────────────────────────

def render_tables(ranked, date_str, vix, regime_counts):
    sections = []
    for tf_key, tf_info in TIMEFRAMES.items():
        sections.append(_table_section(tf_key, tf_info, ranked.get(tf_key, [])))

    market_bar = _market_summary_bar(vix, date_str, regime_counts)
    nav = ' · '.join(
        f'<a href="#section-{tf}" style="color:{BLUE};text-decoration:none;">'
        f'{TIMEFRAMES[tf]["label"]}</a>'
        for tf in TIMEFRAMES)
    body = '\n'.join(sections)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Options Daily Briefing — {date_str}</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:{BG}; color:{TEXT};
          font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
  ::-webkit-scrollbar {{ width:6px; height:6px; }}
  ::-webkit-scrollbar-track {{ background:{SURFACE}; }}
  ::-webkit-scrollbar-thumb {{ background:{BORDER}; border-radius:3px; }}
  .pick-row:hover {{ filter:brightness(1.12); transition:filter 0.12s; }}
  thead th {{ position:sticky; top:0; z-index:2; }}
  p {{ margin:0; }}
</style>
</head>
<body>
<div style="max-width:1600px;margin:0 auto;padding:24px 20px;">

  <div style="display:flex;justify-content:space-between;align-items:flex-start;
              margin-bottom:24px;flex-wrap:wrap;gap:12px;">
    <div>
      <h1 style="font-size:26px;font-weight:800;color:{TEXT};">📊 Options Daily Briefing</h1>
      <div style="color:{TEXT2};font-size:13px;margin-top:4px;">
        Best options to buy today · Ranked by conviction score · {nav}
      </div>
    </div>
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
      <input oninput="filterAll(this.value)" placeholder="Filter by ticker..."
             style="background:{SURFACE};border:1px solid {BORDER};color:{TEXT};
                    border-radius:6px;padding:7px 12px;font-size:13px;width:180px;outline:none;"/>
      <span style="color:{TEXT2};font-size:12px;">Click any row for full analysis ↕</span>
    </div>
  </div>

  {market_bar}
  {body}

  <div style="color:{TEXT3};font-size:11px;text-align:center;
              padding:20px 0 8px;border-top:1px solid {BORDER};">
    Generated {date_str} · Educational purposes only · Not financial advice · Always manage risk
  </div>
</div>
{JS}
</body>
</html>"""

# ─── Portfolio Panel (live mode) ─────────────────────────────────────────────

def _portfolio_panel(summary: dict, positions: list, broker_mode: str, connected: bool):
    total   = summary.get('total_pnl', 0)
    unreal  = summary.get('unrealized_pnl', 0)
    real    = summary.get('realized_pnl', 0)
    opens   = summary.get('open_positions', 0)
    win_r   = summary.get('win_rate', 0)
    pf      = summary.get('profit_factor', 0)
    closed  = summary.get('closed_trades', 0)

    tc      = GREEN if total >= 0 else RED
    uc      = GREEN if unreal >= 0 else RED
    rc      = GREEN if real >= 0 else RED
    mode_c  = YELLOW if 'PAPER' in broker_mode.upper() else RED
    conn_c  = GREEN if connected else YELLOW

    # Position rows
    pos_rows = ''
    for p in positions:
        pnl  = p.get('unrealized_pnl', 0)
        pct  = p.get('unrealized_pct', 0)
        pc   = GREEN if pnl >= 0 else RED
        cp   = p.get('current_price', p['entry_price'])
        tp   = p['target_price']
        sp   = p['stop_price']
        ptt  = p.get('pct_to_target', 0)
        tid  = p['id']
        pos_rows += f"""
        <tr style="border-bottom:1px solid {BORDER};">
          <td style="padding:8px;color:{BLUE};font-weight:700;">{p['ticker']}</td>
          <td style="padding:8px;">{_badge(p['option_type'], GREEN if p['option_type']=='CALL' else RED)}</td>
          <td style="padding:8px;color:{TEXT2};">${p['strike']:.0f} {p['expiry']}</td>
          <td style="padding:8px;color:{ORANGE};">${p['entry_price']:.2f}</td>
          <td style="padding:8px;color:{TEXT};" id="pos-price-{tid}">${cp:.2f}</td>
          <td style="padding:8px;color:{GREEN};">${tp:.2f}</td>
          <td style="padding:8px;color:{RED};">${sp:.2f}</td>
          <td style="padding:8px;color:{pc};font-weight:700;" id="pos-pnl-{tid}">
            {'+'if pnl>=0 else ''}{pnl:.2f} ({'+' if pct>=0 else ''}{pct:.1f}%)
          </td>
          <td style="padding:8px;color:{TEXT2};">{p.get('contracts',1)} ct</td>
          <td style="padding:8px;">
            <button onclick="closePosition({tid})"
                    style="background:#3d1a1a;color:{RED};border:1px solid {RED}44;
                           border-radius:4px;padding:4px 10px;font-size:11px;cursor:pointer;">
              Close
            </button>
          </td>
        </tr>"""

    pos_table = ''
    if positions:
        pos_table = f"""
        <div style="margin-top:16px;overflow-x:auto;">
          <table style="width:100%;border-collapse:collapse;font-size:12px;
                        font-family:'SF Mono',Consolas,monospace;">
            <thead>
              <tr style="background:{SURFACE2};">
                <th style="padding:8px;color:{TEXT2};text-align:left;">TICKER</th>
                <th style="padding:8px;color:{TEXT2};">TYPE</th>
                <th style="padding:8px;color:{TEXT2};">STRIKE/EXP</th>
                <th style="padding:8px;color:{ORANGE};">ENTRY</th>
                <th style="padding:8px;color:{TEXT};">CURRENT</th>
                <th style="padding:8px;color:{GREEN};">TARGET</th>
                <th style="padding:8px;color:{RED};">STOP</th>
                <th style="padding:8px;color:{TEXT2};">UNREAL P&L</th>
                <th style="padding:8px;color:{TEXT2};">SIZE</th>
                <th style="padding:8px;color:{TEXT2};">ACTION</th>
              </tr>
            </thead>
            <tbody>{pos_rows}</tbody>
          </table>
        </div>"""
    else:
        pos_table = f'<div style="color:{TEXT3};padding:16px 0;font-size:13px;">No open positions</div>'

    return f"""
  <div id="portfolio-panel" style="background:{SURFACE};border:1px solid {BORDER};
              border-radius:10px;padding:18px 24px;margin-bottom:28px;">
    <div style="display:flex;justify-content:space-between;align-items:center;
                flex-wrap:wrap;gap:12px;margin-bottom:4px;">
      <div style="display:flex;align-items:center;gap:12px;">
        <h2 style="font-size:18px;font-weight:800;color:{TEXT};margin:0;">💼 Portfolio</h2>
        <span style="background:{mode_c}22;color:{mode_c};border:1px solid {mode_c}44;
                     border-radius:4px;padding:2px 10px;font-size:11px;font-weight:700;">
          {broker_mode}
        </span>
        <span style="color:{conn_c};font-size:12px;">
          {'● Live' if connected else '○ Demo'}
        </span>
      </div>
      <div style="display:flex;gap:6px;">
        <button onclick="exportPortfolio()"
                style="background:{SURFACE2};color:{TEXT2};border:1px solid {BORDER};
                       border-radius:5px;padding:5px 12px;font-size:11px;cursor:pointer;">
          Export JSON
        </button>
        <button onclick="togglePortfolioDetail()"
                style="background:{SURFACE2};color:{TEXT2};border:1px solid {BORDER};
                       border-radius:5px;padding:5px 12px;font-size:11px;cursor:pointer;"
                id="port-toggle-btn">▼ Show Positions</button>
      </div>
    </div>

    <!-- Summary stats row -->
    <div style="display:flex;flex-wrap:wrap;gap:20px;margin-top:14px;">
      <div>
        <div style="color:{TEXT3};font-size:10px;text-transform:uppercase;letter-spacing:1px;">Total P&L</div>
        <div style="color:{tc};font-size:24px;font-weight:800;" id="port-total-pnl">
          {'+'if total>=0 else ''}${total:,.2f}
        </div>
      </div>
      <div>
        <div style="color:{TEXT3};font-size:10px;text-transform:uppercase;letter-spacing:1px;">Unrealized</div>
        <div style="color:{uc};font-size:18px;font-weight:700;" id="port-unrealized">
          {'+'if unreal>=0 else ''}${unreal:,.2f}
        </div>
      </div>
      <div>
        <div style="color:{TEXT3};font-size:10px;text-transform:uppercase;letter-spacing:1px;">Realized</div>
        <div style="color:{rc};font-size:18px;font-weight:700;" id="port-realized">
          {'+'if real>=0 else ''}${real:,.2f}
        </div>
      </div>
      <div>
        <div style="color:{TEXT3};font-size:10px;text-transform:uppercase;letter-spacing:1px;">Open Positions</div>
        <div style="color:{TEXT};font-size:18px;font-weight:700;" id="port-open">{opens}</div>
      </div>
      <div>
        <div style="color:{TEXT3};font-size:10px;text-transform:uppercase;letter-spacing:1px;">Win Rate</div>
        <div style="color:{GREEN if win_r >= 50 else YELLOW};font-size:18px;font-weight:700;" id="port-winrate">
          {win_r:.0f}% <span style="font-size:12px;color:{TEXT3};">({closed} trades)</span>
        </div>
      </div>
      <div>
        <div style="color:{TEXT3};font-size:10px;text-transform:uppercase;letter-spacing:1px;">Profit Factor</div>
        <div style="color:{GREEN if pf >= 1.5 else (YELLOW if pf >= 1.0 else RED)};font-size:18px;font-weight:700;" id="port-pf">
          {pf:.2f}x
        </div>
      </div>
      <div style="margin-left:auto;display:flex;align-items:center;gap:8px;">
        <div style="color:{TEXT3};font-size:11px;">Last update:</div>
        <div style="color:{TEXT2};font-size:11px;" id="last-update">—</div>
      </div>
    </div>

    <!-- Open positions table (hidden by default, toggled) -->
    <div id="portfolio-detail" style="display:none;">
      {pos_table}
    </div>
  </div>"""


# ─── Invest Modal HTML ────────────────────────────────────────────────────────

INVEST_MODAL = f"""
<!-- Invest Modal -->
<div id="invest-modal" style="display:none;position:fixed;inset:0;z-index:9999;
     background:rgba(0,0,0,0.75);backdrop-filter:blur(4px);">
  <div style="background:{SURFACE};border:1px solid {BORDER};border-radius:12px;
              max-width:560px;width:90%;margin:60px auto;padding:28px;
              box-shadow:0 20px 60px rgba(0,0,0,0.6);max-height:80vh;overflow-y:auto;">

    <!-- Header -->
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
      <div>
        <h2 style="font-size:20px;font-weight:800;color:{TEXT};" id="modal-title">Place Trade</h2>
        <div id="modal-mode-badge" style="margin-top:6px;"></div>
      </div>
      <button onclick="closeModal()" style="background:{SURFACE2};color:{TEXT2};
              border:1px solid {BORDER};border-radius:6px;padding:6px 12px;cursor:pointer;">✕</button>
    </div>

    <!-- Trade summary -->
    <div style="background:{SURFACE2};border-radius:8px;padding:16px;margin-bottom:20px;">
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:12px;">
        <div>
          <div style="color:{TEXT3};font-size:10px;text-transform:uppercase;">Entry</div>
          <div style="color:{ORANGE};font-size:18px;font-weight:700;" id="modal-entry">—</div>
        </div>
        <div>
          <div style="color:{TEXT3};font-size:10px;text-transform:uppercase;">Target</div>
          <div style="color:{GREEN};font-size:18px;font-weight:700;" id="modal-target">—</div>
        </div>
        <div>
          <div style="color:{TEXT3};font-size:10px;text-transform:uppercase;">Stop</div>
          <div style="color:{RED};font-size:18px;font-weight:700;" id="modal-stop">—</div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
        <div>
          <div style="color:{TEXT3};font-size:10px;">Expiry / DTE</div>
          <div style="color:{TEXT2};font-size:13px;" id="modal-expiry">—</div>
        </div>
        <div>
          <div style="color:{TEXT3};font-size:10px;">P(Touch Target)</div>
          <div style="color:{TEAL};font-size:13px;" id="modal-ptouch">—</div>
        </div>
        <div>
          <div style="color:{TEXT3};font-size:10px;">Score</div>
          <div style="font-size:13px;" id="modal-score">—</div>
        </div>
      </div>
    </div>

    <!-- Contracts input -->
    <div style="margin-bottom:20px;">
      <label style="color:{TEXT};font-size:13px;font-weight:600;">Number of Contracts</label>
      <div style="display:flex;gap:10px;margin-top:8px;align-items:center;">
        <input type="number" id="modal-contracts" value="1" min="1" max="100"
               style="background:{SURFACE2};border:1px solid {BORDER};color:{TEXT};
                      border-radius:6px;padding:8px 12px;font-size:16px;width:100px;outline:none;"/>
        <div>
          <div style="color:{TEXT3};font-size:11px;">Total cost</div>
          <div style="color:{ORANGE};font-size:16px;font-weight:700;" id="modal-total-cost">—</div>
        </div>
        <div>
          <div style="color:{TEXT3};font-size:11px;">Max loss</div>
          <div style="color:{RED};font-size:16px;font-weight:700;" id="modal-max-loss">—</div>
        </div>
        <div>
          <div style="color:{TEXT3};font-size:11px;">Max gain</div>
          <div style="color:{GREEN};font-size:16px;font-weight:700;" id="modal-max-gain">—</div>
        </div>
      </div>
    </div>

    <!-- Risk warning -->
    <div id="modal-warning" style="background:#3d1a1a;border-left:3px solid {RED};
         border-radius:0 6px 6px 0;padding:10px 14px;margin-bottom:20px;font-size:12px;
         color:{RED};display:none;">
      ⚠ LIVE TRADING — This will place a REAL order with REAL money.
      Automatic stop-loss and take-profit orders will be set.
    </div>

    <!-- Confirm button -->
    <button id="modal-confirm-btn" onclick="confirmInvest()"
            style="width:100%;padding:14px;border-radius:8px;border:none;
                   font-size:15px;font-weight:800;cursor:pointer;letter-spacing:0.5px;">
      Confirm Order
    </button>

    <div style="color:{TEXT3};font-size:11px;text-align:center;margin-top:12px;">
      Auto stop-loss and take-profit will be set · 1 contract = 100 shares
    </div>
  </div>
</div>"""


# ─── Live JavaScript ──────────────────────────────────────────────────────────

def _live_js(broker_mode: str, connected: bool):
    is_paper = 'PAPER' in broker_mode.upper() or not connected
    paper_str = 'true' if is_paper else 'false'
    return f"""
<script>
// ── State ────────────────────────────────────────────────────────────────────
let _currentTrade = null;
const IS_PAPER = {paper_str};

// ── SSE live updates ──────────────────────────────────────────────────────────
(function connectSSE() {{
  const src = new EventSource('/api/stream');
  src.onmessage = function(e) {{
    try {{
      const msg = JSON.parse(e.data);
      handleLiveUpdate(msg);
    }} catch(err) {{}}
  }};
  src.onerror = function() {{
    // Reconnect after 5s
    src.close();
    setTimeout(connectSSE, 5000);
  }};
}})();

function handleLiveUpdate(msg) {{
  const now = new Date().toLocaleTimeString();
  const el = document.getElementById('last-update');
  if (el) el.textContent = now;

  if (msg.type === 'portfolio' || msg.type === 'init') {{
    updatePortfolioUI(msg.summary || {{}}, msg.positions || []);
  }}
  if (msg.type === 'position_closed') {{
    showToast(msg.reason === 'target_hit'
      ? '✅ TARGET HIT — Position closed for profit!'
      : '🛑 STOP HIT — Position closed at stop-loss.',
      msg.reason === 'target_hit' ? 'green' : 'red');
  }}
  if (msg.type === 'scan') {{
    showToast(`📊 Market re-scanned — ${{msg.picks ? JSON.stringify(msg.picks) : ''}}`, 'blue');
  }}
}}

function updatePortfolioUI(summary, positions) {{
  const set = (id, val) => {{ const el = document.getElementById(id); if(el) el.textContent = val; }};
  const t = summary.total_pnl || 0;
  const u = summary.unrealized_pnl || 0;
  const r = summary.realized_pnl || 0;
  set('port-total-pnl',  (t>=0?'+':'') + '$' + t.toFixed(2));
  set('port-unrealized', (u>=0?'+':'') + '$' + u.toFixed(2));
  set('port-realized',   (r>=0?'+':'') + '$' + r.toFixed(2));
  set('port-open',       summary.open_positions || 0);
  set('port-winrate',    (summary.win_rate||0).toFixed(0) + '%');
  set('port-pf',         (summary.profit_factor||0).toFixed(2) + 'x');
  // Update colours
  const tEl = document.getElementById('port-total-pnl');
  if (tEl) tEl.style.color = t >= 0 ? '{GREEN}' : '{RED}';
  // Update position prices
  (positions || []).forEach(p => {{
    const prEl = document.getElementById('pos-price-' + p.id);
    if (prEl) prEl.textContent = '$' + (p.current_price || p.entry_price).toFixed(2);
    const pnlEl = document.getElementById('pos-pnl-' + p.id);
    if (pnlEl) {{
      const pnl = p.unrealized_pnl || 0;
      pnlEl.textContent = (pnl>=0?'+':'') + '$' + pnl.toFixed(2) +
                          ' (' + (pnl>=0?'+':'') + (p.unrealized_pct||0).toFixed(1) + '%)';
      pnlEl.style.color = pnl >= 0 ? '{GREEN}' : '{RED}';
    }}
  }});
}}

// ── Invest Modal ──────────────────────────────────────────────────────────────
function openInvestModal(tradeData) {{
  _currentTrade = tradeData;
  const m = document.getElementById('invest-modal');
  const entry  = tradeData.entry  || 0;
  const target = tradeData.target || 0;
  const stop   = tradeData.stop   || 0;

  document.getElementById('modal-title').textContent =
    `${{tradeData.ticker}} — ${{tradeData.option_type}} $$${{tradeData.strike}} ${{tradeData.expiry}}`;

  const modeBadge = document.getElementById('modal-mode-badge');
  modeBadge.innerHTML = IS_PAPER
    ? `<span style="background:{YELLOW}22;color:{YELLOW};border:1px solid {YELLOW}44;
         border-radius:4px;padding:2px 10px;font-size:11px;font-weight:700;">
         📄 PAPER TRADING — No real money</span>`
    : `<span style="background:{RED}22;color:{RED};border:1px solid {RED}44;
         border-radius:4px;padding:2px 10px;font-size:11px;font-weight:700;">
         ⚠ LIVE TRADING — REAL MONEY</span>`;

  document.getElementById('modal-entry').textContent  = '$' + entry.toFixed(2);
  document.getElementById('modal-target').textContent = '$' + target.toFixed(2);
  document.getElementById('modal-stop').textContent   = '$' + stop.toFixed(2);
  document.getElementById('modal-expiry').textContent =
    (tradeData.expiry||'') + ' (' + (tradeData.dte||0) + 'd)';
  document.getElementById('modal-ptouch').textContent = (tradeData.p_touch||0) + '%';

  const scoreEl = document.getElementById('modal-score');
  const score = tradeData.score || 0;
  scoreEl.textContent = score + '/100';
  scoreEl.style.color = score >= 75 ? '{GREEN}' : score >= 55 ? '{YELLOW}' : '{TEXT2}';

  document.getElementById('modal-contracts').value = 1;
  updateModalCosts(entry, target, stop, 1);

  // Wire up contract count change
  document.getElementById('modal-contracts').oninput = function() {{
    updateModalCosts(entry, target, stop, parseInt(this.value)||1);
  }};

  // Warning for live mode
  const warn = document.getElementById('modal-warning');
  warn.style.display = IS_PAPER ? 'none' : 'block';

  // Confirm button style
  const btn = document.getElementById('modal-confirm-btn');
  if (IS_PAPER) {{
    btn.style.background = 'linear-gradient(135deg, {GREEN}, {TEAL})';
    btn.style.color = '#000';
    btn.textContent = '✓ Place Paper Order';
  }} else {{
    btn.style.background = 'linear-gradient(135deg, {RED}, #c0392b)';
    btn.style.color = '#fff';
    btn.textContent = '⚠ Place LIVE Order';
  }}

  m.style.display = 'block';
}}

function updateModalCosts(entry, target, stop, contracts) {{
  const mult = 100; // 1 contract = 100 shares
  const cost  = entry  * mult * contracts;
  const gain  = (target - entry) * mult * contracts;
  const loss  = (entry  - stop)  * mult * contracts;
  document.getElementById('modal-total-cost').textContent = '$' + cost.toFixed(0);
  document.getElementById('modal-max-gain').textContent   = '+$' + gain.toFixed(0);
  document.getElementById('modal-max-loss').textContent   = '-$' + loss.toFixed(0);
}}

function closeModal() {{
  document.getElementById('invest-modal').style.display = 'none';
  _currentTrade = null;
}}

async function confirmInvest() {{
  if (!_currentTrade) return;
  const contracts = parseInt(document.getElementById('modal-contracts').value) || 1;
  const btn = document.getElementById('modal-confirm-btn');
  btn.disabled = true;
  btn.textContent = 'Placing order...';

  const payload = {{
    ...(_currentTrade),
    contracts,
    entry_price:  _currentTrade.entry,
    target_price: _currentTrade.target,
    stop_price:   _currentTrade.stop,
    confirmed_live: !IS_PAPER,
  }};

  try {{
    const resp = await fetch('/api/order', {{
      method:  'POST',
      headers: {{'Content-Type': 'application/json'}},
      body:    JSON.stringify(payload),
    }});
    const data = await resp.json();
    if (data.success) {{
      closeModal();
      showToast(`✅ Order placed: ${{contracts}}x ${{_currentTrade.ticker}} ${{_currentTrade.option_type}}` +
                (data.demo ? ' (PAPER)' : ' (LIVE)'), 'green');
    }} else {{
      btn.disabled = false;
      btn.textContent = 'Retry — Error: ' + (data.message || 'unknown');
      btn.style.background = '{RED}';
    }}
  }} catch(err) {{
    btn.disabled = false;
    btn.textContent = 'Network error — retry';
    btn.style.background = '{RED}';
  }}
}}

// Close modal on backdrop click
document.getElementById('invest-modal').addEventListener('click', function(e) {{
  if (e.target === this) closeModal();
}});

// ── Close position ────────────────────────────────────────────────────────────
async function closePosition(tradeId) {{
  if (!confirm('Close this position at current market price?')) return;
  const resp = await fetch('/api/close/' + tradeId, {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{reason: 'manual'}}),
  }});
  const data = await resp.json();
  if (data.success) {{
    showToast('Position closed at $' + data.exit_price, 'orange');
    setTimeout(() => location.reload(), 1500);
  }}
}}

// ── Portfolio UI toggles ──────────────────────────────────────────────────────
function togglePortfolioDetail() {{
  const d   = document.getElementById('portfolio-detail');
  const btn = document.getElementById('port-toggle-btn');
  const open = d.style.display !== 'none';
  d.style.display = open ? 'none' : 'block';
  btn.textContent  = open ? '▼ Show Positions' : '▲ Hide Positions';
}}

async function exportPortfolio() {{
  const resp = await fetch('/api/export');
  const data = await resp.json();
  showToast('Portfolio exported to: ' + data.path, 'blue');
}}

// ── Sort & Filter (same as before) ───────────────────────────────────────────
function toggleDetail(uid) {{
  const row   = document.getElementById('detail-' + uid);
  const arrow = document.getElementById('arrow-' + uid);
  const open  = row.style.display !== 'none';
  row.style.display   = open ? 'none' : 'table-row';
  arrow.textContent   = open ? '▼' : '▲';
  arrow.style.color   = open ? '#8b949e' : '#58a6ff';
}}

function sortTable(tfKey, colIdx) {{
  const tbody = document.getElementById('tbody-' + tfKey);
  const allRows = Array.from(tbody.children);
  const pairs = [];
  for (let i = 0; i < allRows.length; i += 2) {{
    pairs.push([allRows[i], allRows[i+1]]);
  }}
  const asc = tbody.dataset.sortCol == colIdx && tbody.dataset.sortDir == 'asc';
  tbody.dataset.sortCol = colIdx; tbody.dataset.sortDir = asc ? 'desc' : 'asc';
  pairs.sort((a, b) => {{
    const av = a[0].cells[colIdx].textContent.replace(/[^0-9.\-]/g, '');
    const bv = b[0].cells[colIdx].textContent.replace(/[^0-9.\-]/g, '');
    const an = parseFloat(av) || av; const bn = parseFloat(bv) || bv;
    return asc ? (an < bn ? 1 : an > bn ? -1 : 0) : (an > bn ? 1 : an < bn ? -1 : 0);
  }});
  pairs.forEach(([s, d]) => {{ tbody.appendChild(s); tbody.appendChild(d); }});
}}

function filterAll(val) {{
  val = val.toLowerCase();
  document.querySelectorAll('.pick-row').forEach(r => {{
    const ticker = r.dataset.ticker.toLowerCase();
    const show = !val || ticker.includes(val);
    r.style.display = show ? '' : 'none';
    const uid = r.dataset.uid;
    const detRow = document.getElementById('detail-' + uid);
    if (detRow && !show) detRow.style.display = 'none';
  }});
}}

// ── Toast notifications ───────────────────────────────────────────────────────
function showToast(msg, color) {{
  const colors = {{ green: '{GREEN}', red: '{RED}', orange: '{ORANGE}', blue: '{BLUE}', yellow: '{YELLOW}' }};
  const c = colors[color] || '{TEXT}';
  const t = document.createElement('div');
  t.style.cssText = `position:fixed;bottom:24px;right:24px;z-index:99999;
    background:{SURFACE};border:1px solid ${{c}};border-left:4px solid ${{c}};
    color:{TEXT};border-radius:8px;padding:12px 20px;font-size:13px;font-weight:600;
    box-shadow:0 8px 24px rgba(0,0,0,0.4);max-width:400px;transition:opacity 0.3s;`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => {{ t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }}, 4000);
}}
</script>"""


# ─── render_live_dashboard (for server.py) ───────────────────────────────────

def render_live_dashboard(ranked, date_str, vix, regime_counts,
                           portfolio_summary, open_positions,
                           broker_mode='PAPER', broker_connected=False):
    """
    Render the full live HTML dashboard.
    Called by server.py on every page load (data is re-fetched each request).
    SSE keeps data updated without page reloads.
    """
    sections = []
    for tf_key, tf_info in TIMEFRAMES.items():
        sections.append(_table_section(tf_key, tf_info, ranked.get(tf_key, [])))

    market_bar   = _market_summary_bar(vix, date_str, regime_counts)
    port_panel   = _portfolio_panel(portfolio_summary, open_positions,
                                     broker_mode, broker_connected)
    nav = ' · '.join(
        f'<a href="#section-{tf}" style="color:{BLUE};text-decoration:none;">'
        f'{TIMEFRAMES[tf]["label"]}</a>'
        for tf in TIMEFRAMES)
    body = '\n'.join(sections)
    live_js = _live_js(broker_mode, broker_connected)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Options Daily Briefing — {date_str}</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:{BG}; color:{TEXT};
          font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
  ::-webkit-scrollbar {{ width:6px; height:6px; }}
  ::-webkit-scrollbar-track {{ background:{SURFACE}; }}
  ::-webkit-scrollbar-thumb {{ background:{BORDER}; border-radius:3px; }}
  .pick-row:hover {{ filter:brightness(1.12); transition:filter 0.12s; }}
  thead th {{ position:sticky; top:0; z-index:2; }}
  p {{ margin:0; }}
</style>
</head>
<body>
{INVEST_MODAL}
<div style="max-width:1600px;margin:0 auto;padding:24px 20px;">

  <div style="display:flex;justify-content:space-between;align-items:flex-start;
              margin-bottom:24px;flex-wrap:wrap;gap:12px;">
    <div>
      <h1 style="font-size:26px;font-weight:800;color:{TEXT};">📊 Options Daily Briefing</h1>
      <div style="color:{TEXT2};font-size:13px;margin-top:4px;">
        Best options to buy today · Ranked by conviction score · {nav}
      </div>
    </div>
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
      <input oninput="filterAll(this.value)" placeholder="Filter by ticker..."
             style="background:{SURFACE};border:1px solid {BORDER};color:{TEXT};
                    border-radius:6px;padding:7px 12px;font-size:13px;width:180px;outline:none;"/>
      <div style="color:{TEXT2};font-size:11px;">
        🔴 Live updates via SSE &nbsp;·&nbsp; Click row = analysis &nbsp;·&nbsp; INVEST = place order
      </div>
    </div>
  </div>

  {port_panel}
  {market_bar}
  {body}

  <div style="color:{TEXT3};font-size:11px;text-align:center;
              padding:20px 0 8px;border-top:1px solid {BORDER};">
    Live server · Data updates every 60s · Portfolio stored at ~/.options_briefing/ ·
    Educational purposes only · Not financial advice · Always manage risk
  </div>
</div>
{live_js}
</body>
</html>"""
