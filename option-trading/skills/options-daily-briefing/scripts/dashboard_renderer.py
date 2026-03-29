"""
HTML Dashboard Renderer
========================
Generates a single-file, self-contained HTML daily briefing dashboard.
All charts are embedded as base64 PNG — no server or CDN needed.
Open the output .html file in any browser.
"""

from datetime import datetime


# ─── Score color helpers ──────────────────────────────────────────────────────

def score_color(score):
    if score >= 75: return '#3fb950'
    if score >= 55: return '#e3b341'
    return '#f85149'

def score_label(score):
    if score >= 75: return 'STRONG'
    if score >= 55: return 'MODERATE'
    return 'WEAK'

def trend_badge(trend, strength):
    colors = {'bullish': '#3fb950', 'bearish': '#f85149', 'sideways': '#e3b341'}
    c = colors.get(trend, '#8b949e')
    return f'<span style="background:{c}22;color:{c};border:1px solid {c};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700">{strength.upper()} {trend.upper()}</span>'

def vol_badge(vol_regime):
    colors = {'low': '#3fb950', 'normal': '#58a6ff', 'elevated': '#e3b341', 'high': '#f85149'}
    c = colors.get(vol_regime, '#8b949e')
    return f'<span style="background:{c}22;color:{c};border:1px solid {c};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700">VOL {vol_regime.upper()}</span>'

def prob_bar(pct, color):
    return f'''
    <div style="background:#21262d;border-radius:6px;height:8px;margin:4px 0;overflow:hidden">
      <div style="background:{color};width:{pct}%;height:100%;border-radius:6px;transition:width 0.4s"></div>
    </div>'''


# ─── Main Dashboard Builder ───────────────────────────────────────────────────

def render_dashboard(recs, market_overview_b64, date_str, vix):
    """
    recs: list of recommendation dicts (from analysis_engine.build_recommendation)
          each rec also has keys: 'chart_price', 'chart_pnl', 'chart_prob' (base64)
    market_overview_b64: base64 PNG of the market overview mini-chart
    """
    timeframe_order = ['short', 'mid', 'long']
    timeframe_labels = {
        'short': '⚡ SHORT TERM  (7–21 Days)',
        'mid':   '📊 MID TERM  (4 Weeks – 3 Months)',
        'long':  '🏔️ LONG TERM  (3 Months+)',
    }
    timeframe_descriptions = {
        'short': 'Weekly to monthly options for fast momentum plays. High gamma, responds quickly.',
        'mid':   'The premium-seller sweet spot. Best balance of theta, delta, and time for the move.',
        'long':  'LEAPS-style directional positions. Deep ITM, low theta drag, built to ride big trends.',
    }

    # Group by timeframe
    by_tf = {}
    for r in recs:
        by_tf.setdefault(r['timeframe'], []).append(r)

    vix_color = '#f85149' if vix and vix > 25 else '#e3b341' if vix and vix > 18 else '#3fb950'
    vix_label = f'VIX {vix:.1f}' if vix else 'VIX N/A'

    sections_html = ''
    for tf in timeframe_order:
        tf_recs = by_tf.get(tf, [])
        if not tf_recs:
            continue

        cards_html = ''
        for rec in tf_recs:
            opt_dir_color = '#3fb950' if rec['opt_type'] == 'CALL' else '#f85149'
            s_color = score_color(rec['score'])
            s_label = score_label(rec['score'])

            # Reasoning bullets
            reasoning_html = ''.join(
                f'<li style="margin:6px 0;line-height:1.5">{line}</li>'
                for line in rec['reasoning']
            )

            # Greeks row
            greeks_html = f'''
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:10px 0">
              {greek_box("Δ Delta",  rec["delta"], "#58a6ff")}
              {greek_box("Γ Gamma",  rec["gamma"], "#bc8cff")}
              {greek_box("Θ Theta",  rec["theta"], "#f85149")}
              {greek_box("ν Vega",   rec["vega"],  "#e3b341")}
            </div>'''

            # Probability section
            prob_html = f'''
            <div style="background:#0d1117;border-radius:8px;padding:12px;margin:10px 0">
              <div style="font-size:11px;color:#8b949e;font-weight:700;letter-spacing:1px;margin-bottom:8px">PROBABILITY ANALYSIS</div>
              <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px">
                {prob_card("TOUCH TARGET", rec["prob_touch"], "#3fb950", "before expiry")}
                {prob_card("PROFIT AT EXPIRY", rec["prob_profit"], "#58a6ff", "breakeven exceeded")}
                {prob_card("EXPIRE ITM", rec["prob_itm"], "#bc8cff", "finishes in the money")}
              </div>
            </div>'''

            cards_html += f'''
            <div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
                        margin-bottom:28px;overflow:hidden">

              <!-- Card header -->
              <div style="background:#0d1117;padding:16px 20px;display:flex;
                          justify-content:space-between;align-items:center;
                          border-bottom:1px solid #21262d">
                <div style="display:flex;align-items:center;gap:12px">
                  <span style="font-size:22px;font-weight:800;color:#c9d1d9">{rec["ticker"]}</span>
                  <span style="background:{opt_dir_color}22;color:{opt_dir_color};
                               border:1px solid {opt_dir_color};padding:3px 12px;
                               border-radius:6px;font-size:13px;font-weight:700">
                    {rec["opt_type"]}
                  </span>
                  {trend_badge(rec["regime"]["trend"], rec["regime"]["strength"])}
                  {vol_badge(rec["regime"]["vol_regime"])}
                </div>
                <div style="text-align:right">
                  <div style="font-size:24px;font-weight:800;color:{s_color}">{rec["score"]}/100</div>
                  <div style="font-size:11px;color:{s_color};font-weight:700">{s_label} SETUP</div>
                </div>
              </div>

              <!-- Trade details row -->
              <div style="display:grid;grid-template-columns:repeat(5,1fr);
                          gap:0;border-bottom:1px solid #21262d">
                {trade_detail_box("CONTRACT", rec["option_label"], "#c9d1d9", small=True)}
                {trade_detail_box("ENTRY PRICE", f"${rec['entry_price']:.2f}", "#e3b341", sublabel="buy at mid")}
                {trade_detail_box("TARGET SELL", f"${rec['target_price']:.2f}", "#3fb950", sublabel=f"stock at {rec['price_target']:.2f}")}
                {trade_detail_box("STOP LOSS", f"${rec['stop_price']:.2f}", "#f85149", sublabel=f"stock at {rec['price_stop']:.2f}")}
                {trade_detail_box("RISK / REWARD", f"{rec['rr_ratio']:.1f} : 1", "#58a6ff", sublabel=f"+${rec['max_gain']:.0f} / -${rec['max_loss']:.0f}")}
              </div>

              <!-- Charts row -->
              <div style="padding:16px">
                <div style="margin-bottom:8px;font-size:11px;color:#8b949e;
                            font-weight:700;letter-spacing:1px">PRICE CHART + INDICATORS</div>
                <img src="data:image/png;base64,{rec.get('chart_price','')}"
                     style="width:100%;border-radius:8px;border:1px solid #30363d" />
              </div>

              <!-- P&L + Probability side by side -->
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:0;
                          padding:0 16px 16px">
                <div>
                  <div style="font-size:11px;color:#8b949e;font-weight:700;
                              letter-spacing:1px;margin-bottom:8px">P&L DIAGRAM</div>
                  <img src="data:image/png;base64,{rec.get('chart_pnl','')}"
                       style="width:100%;border-radius:8px;border:1px solid #30363d" />
                </div>
                <div style="padding-left:16px">
                  <div style="font-size:11px;color:#8b949e;font-weight:700;
                              letter-spacing:1px;margin-bottom:8px">PROBABILITY DISTRIBUTION</div>
                  <img src="data:image/png;base64,{rec.get('chart_prob','')}"
                       style="width:100%;border-radius:8px;border:1px solid #30363d" />
                </div>
              </div>

              <!-- Greeks -->
              <div style="padding:0 16px">
                <div style="font-size:11px;color:#8b949e;font-weight:700;
                            letter-spacing:1px;margin-bottom:4px">OPTION GREEKS</div>
                {greeks_html}
              </div>

              <!-- Probabilities -->
              <div style="padding:0 16px 16px">
                {prob_html}
              </div>

              <!-- IV badge -->
              <div style="padding:0 16px 8px">
                <div style="display:inline-block;background:#21262d;border-radius:6px;
                            padding:6px 12px;font-size:12px;color:#8b949e">
                  <strong style="color:#c9d1d9">IV: {rec["iv"]:.0f}%</strong>
                  &nbsp;—&nbsp; {rec["iv_assessment"]}
                  &nbsp;&nbsp;|&nbsp;&nbsp;
                  <strong style="color:#c9d1d9">Expiry:</strong> {rec["expiry"]}
                  &nbsp;({rec["dte"]} DTE)
                  &nbsp;&nbsp;|&nbsp;&nbsp;
                  <strong style="color:#c9d1d9">1σ Expected Move:</strong>
                  ±${rec["expected_move"]:.2f}
                </div>
              </div>

              <!-- Reasoning -->
              <div style="background:#0d1117;margin:0 16px 16px;border-radius:8px;
                          padding:16px;border:1px solid #21262d">
                <div style="font-size:11px;color:#8b949e;font-weight:700;
                            letter-spacing:1px;margin-bottom:10px">🧠 REASONING & ANALYSIS</div>
                <ul style="margin:0;padding-left:18px;color:#c9d1d9;font-size:13px">
                  {reasoning_html}
                </ul>
              </div>

              <!-- Execution checklist -->
              <div style="background:#161b22;margin:0 16px 16px;border-radius:8px;
                          padding:14px;border:1px solid #30363d">
                <div style="font-size:11px;color:#8b949e;font-weight:700;
                            letter-spacing:1px;margin-bottom:10px">✅ EXECUTION CHECKLIST</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;
                            font-size:12px;color:#8b949e">
                  {checklist_item("Confirm IVR before entry")}
                  {checklist_item("Check options chain liquidity (OI > 500)")}
                  {checklist_item(f"Enter as limit order at ${rec['entry_limit']:.2f} or better")}
                  {checklist_item("Size max 3–5% of account")}
                  {checklist_item(f"Set profit target GTC at ${rec['target_price']:.2f}")}
                  {checklist_item(f"Set stop loss alert at ${rec['stop_price']:.2f}")}
                </div>
              </div>

            </div>'''

        sections_html += f'''
        <div style="margin-bottom:48px">
          <div style="display:flex;align-items:baseline;gap:12px;margin-bottom:6px">
            <h2 style="margin:0;font-size:18px;font-weight:800;color:#c9d1d9">
              {timeframe_labels[tf]}
            </h2>
          </div>
          <p style="margin:0 0 20px;font-size:13px;color:#8b949e">
            {timeframe_descriptions[tf]}
          </p>
          {cards_html}
        </div>'''

    # Market overview banner
    overview_html = f'''
    <div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
                padding:16px 20px;margin-bottom:32px">
      <div style="display:flex;justify-content:space-between;align-items:center;
                  margin-bottom:12px">
        <div>
          <h2 style="margin:0;font-size:14px;font-weight:700;color:#8b949e;
                     letter-spacing:1px">MARKET OVERVIEW</h2>
        </div>
        <div style="display:flex;gap:12px;align-items:center">
          <span style="background:{vix_color}22;color:{vix_color};border:1px solid {vix_color};
                       padding:4px 12px;border-radius:6px;font-size:13px;font-weight:700">
            {vix_label}
          </span>
          <span style="font-size:12px;color:#8b949e">{date_str}</span>
        </div>
      </div>
      <img src="data:image/png;base64,{market_overview_b64}"
           style="width:100%;max-width:700px;border-radius:8px" />
    </div>'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Options Daily Briefing — {date_str}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0d1117;
      color: #c9d1d9;
      font-family: -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      font-size: 14px;
      line-height: 1.6;
    }}
    .header {{
      background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
      border-bottom: 1px solid #30363d;
      padding: 20px 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }}
    .header-left h1 {{
      font-size: 20px;
      font-weight: 800;
      color: #58a6ff;
      letter-spacing: -0.5px;
    }}
    .header-left p {{
      font-size: 12px;
      color: #8b949e;
      margin-top: 2px;
    }}
    .nav {{
      display: flex;
      gap: 8px;
    }}
    .nav a {{
      background: #21262d;
      color: #c9d1d9;
      text-decoration: none;
      padding: 6px 16px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      border: 1px solid #30363d;
      transition: background 0.2s;
    }}
    .nav a:hover {{ background: #30363d; }}
    .container {{
      max-width: 1300px;
      margin: 0 auto;
      padding: 28px 24px 60px;
    }}
    img {{ display: block; max-width: 100%; }}
    .disclaimer {{
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 11px;
      color: #8b949e;
      margin-top: 40px;
      line-height: 1.7;
    }}
  </style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <h1>📈 Options Daily Briefing</h1>
    <p>AI-powered analysis — {date_str} | Review by 9:00 AM before market open</p>
  </div>
  <nav class="nav">
    <a href="#short">⚡ Short Term</a>
    <a href="#mid">📊 Mid Term</a>
    <a href="#long">🏔️ Long Term</a>
  </nav>
</div>

<div class="container">
  {overview_html}

  <div id="short">{sections_html.split('<div style="margin-bottom:48px">')[1] if len(sections_html.split('<div style="margin-bottom:48px">')) > 1 else ""}</div>

  <div class="disclaimer">
    ⚠️ <strong>Risk Disclosure:</strong> This briefing is for informational and educational purposes only.
    Options trading involves significant risk of loss and is not suitable for all investors.
    Probability estimates are based on mathematical models (Black-Scholes) and historical data —
    actual outcomes may differ significantly. Always conduct your own due diligence.
    Past performance does not guarantee future results. Position sizing and risk management
    are your responsibility. Never risk more than you can afford to lose.
  </div>
</div>

</body>
</html>'''

    # Cleaner approach: build sections directly (avoid split hack above)
    return build_clean_html(recs, market_overview_b64, date_str, vix,
                             by_tf, timeframe_order, timeframe_labels,
                             timeframe_descriptions, sections_html, vix_color, vix_label,
                             overview_html)


def build_clean_html(recs, market_overview_b64, date_str, vix,
                     by_tf, timeframe_order, timeframe_labels,
                     timeframe_descriptions, sections_html, vix_color, vix_label,
                     overview_html):
    """Clean, direct HTML builder."""

    all_sections = ''
    for tf in timeframe_order:
        tf_recs = by_tf.get(tf, [])
        if not tf_recs:
            continue

        cards = ''
        for rec in tf_recs:
            opt_dir_color = '#3fb950' if rec['opt_type'] == 'CALL' else '#f85149'
            s_color = score_color(rec['score'])
            s_label = score_label(rec['score'])

            reasoning_html = ''.join(
                f'<li style="margin:6px 0;line-height:1.5">{line}</li>'
                for line in rec['reasoning']
            )

            greeks_row = f'''<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:10px 0">
              {greek_box("Δ Delta",  rec["delta"], "#58a6ff")}
              {greek_box("Γ Gamma",  rec["gamma"], "#bc8cff")}
              {greek_box("Θ Theta",  rec["theta"], "#f85149")}
              {greek_box("ν Vega",   rec["vega"],  "#e3b341")}
            </div>'''

            prob_row = f'''<div style="background:#0d1117;border-radius:8px;padding:12px;margin:10px 0">
              <div style="font-size:11px;color:#8b949e;font-weight:700;letter-spacing:1px;margin-bottom:8px">PROBABILITY ANALYSIS</div>
              <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px">
                {prob_card("TOUCH TARGET", rec["prob_touch"], "#3fb950", "before expiry")}
                {prob_card("PROFIT AT EXPIRY", rec["prob_profit"], "#58a6ff", "breakeven exceeded")}
                {prob_card("EXPIRE ITM", rec["prob_itm"], "#bc8cff", "finishes in the money")}
              </div>
            </div>'''

            cards += f'''
<div style="background:#161b22;border:1px solid #30363d;border-radius:12px;margin-bottom:28px;overflow:hidden">
  <div style="background:#0d1117;padding:16px 20px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #21262d">
    <div style="display:flex;align-items:center;gap:12px">
      <span style="font-size:22px;font-weight:800;color:#c9d1d9">{rec["ticker"]}</span>
      <span style="background:{opt_dir_color}22;color:{opt_dir_color};border:1px solid {opt_dir_color};padding:3px 12px;border-radius:6px;font-size:13px;font-weight:700">{rec["opt_type"]}</span>
      {trend_badge(rec["regime"]["trend"], rec["regime"]["strength"])}
      {vol_badge(rec["regime"]["vol_regime"])}
    </div>
    <div style="text-align:right">
      <div style="font-size:24px;font-weight:800;color:{s_color}">{rec["score"]}/100</div>
      <div style="font-size:11px;color:{s_color};font-weight:700">{s_label} SETUP</div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:0;border-bottom:1px solid #21262d">
    {trade_detail_box("CONTRACT", rec["option_label"], "#c9d1d9", small=True)}
    {trade_detail_box("ENTRY PRICE", f"${rec['entry_price']:.2f}", "#e3b341", sublabel="buy at mid")}
    {trade_detail_box("TARGET SELL", f"${rec['target_price']:.2f}", "#3fb950", sublabel=f"stock → {rec['price_target']:.2f}")}
    {trade_detail_box("STOP LOSS", f"${rec['stop_price']:.2f}", "#f85149", sublabel=f"stock → {rec['price_stop']:.2f}")}
    {trade_detail_box("RISK/REWARD", f"{rec['rr_ratio']:.1f}:1", "#58a6ff", sublabel=f"+${rec['max_gain']:.0f} / -${rec['max_loss']:.0f}")}
  </div>
  <div style="padding:16px">
    <div style="margin-bottom:8px;font-size:11px;color:#8b949e;font-weight:700;letter-spacing:1px">PRICE CHART + TECHNICAL INDICATORS</div>
    <img src="data:image/png;base64,{rec.get("chart_price","")}" style="width:100%;border-radius:8px;border:1px solid #30363d" />
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:0;padding:0 16px 16px">
    <div>
      <div style="font-size:11px;color:#8b949e;font-weight:700;letter-spacing:1px;margin-bottom:8px">P&amp;L DIAGRAM AT EXPIRY</div>
      <img src="data:image/png;base64,{rec.get("chart_pnl","")}" style="width:100%;border-radius:8px;border:1px solid #30363d" />
    </div>
    <div style="padding-left:16px">
      <div style="font-size:11px;color:#8b949e;font-weight:700;letter-spacing:1px;margin-bottom:8px">PROBABILITY DISTRIBUTION</div>
      <img src="data:image/png;base64,{rec.get("chart_prob","")}" style="width:100%;border-radius:8px;border:1px solid #30363d" />
    </div>
  </div>
  <div style="padding:0 16px">
    <div style="font-size:11px;color:#8b949e;font-weight:700;letter-spacing:1px;margin-bottom:4px">OPTION GREEKS</div>
    {greeks_row}
  </div>
  <div style="padding:0 16px 16px">{prob_row}</div>
  <div style="padding:0 16px 8px">
    <div style="display:inline-block;background:#21262d;border-radius:6px;padding:6px 12px;font-size:12px;color:#8b949e">
      <strong style="color:#c9d1d9">IV: {rec["iv"]:.0f}%</strong> &mdash; {rec["iv_assessment"]}
      &nbsp;|&nbsp; <strong style="color:#c9d1d9">Expiry:</strong> {rec["expiry"]} ({rec["dte"]} DTE)
      &nbsp;|&nbsp; <strong style="color:#c9d1d9">1&sigma; Move:</strong> ±${rec["expected_move"]:.2f}
    </div>
  </div>
  <div style="background:#0d1117;margin:0 16px 16px;border-radius:8px;padding:16px;border:1px solid #21262d">
    <div style="font-size:11px;color:#8b949e;font-weight:700;letter-spacing:1px;margin-bottom:10px">🧠 REASONING &amp; ANALYSIS</div>
    <ul style="margin:0;padding-left:18px;color:#c9d1d9;font-size:13px">{reasoning_html}</ul>
  </div>
  <div style="background:#161b22;margin:0 16px 16px;border-radius:8px;padding:14px;border:1px solid #30363d">
    <div style="font-size:11px;color:#8b949e;font-weight:700;letter-spacing:1px;margin-bottom:10px">✅ EXECUTION CHECKLIST</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;color:#8b949e">
      {checklist_item("Confirm IVR is appropriate for this strategy")}
      {checklist_item("Check options chain liquidity (OI &gt; 500)")}
      {checklist_item(f"Enter limit order at ${rec['entry_limit']:.2f} or better")}
      {checklist_item("Size max 3–5% of account per trade")}
      {checklist_item(f"Set profit target GTC at ${rec['target_price']:.2f}")}
      {checklist_item(f"Set stop-loss alert at stock price ${rec['price_stop']:.2f}")}
    </div>
  </div>
</div>'''

        anchor = tf
        all_sections += f'''
<div id="{anchor}" style="margin-bottom:48px">
  <div style="border-left:3px solid #58a6ff;padding-left:14px;margin-bottom:16px">
    <h2 style="margin:0;font-size:18px;font-weight:800;color:#c9d1d9">{timeframe_labels[tf]}</h2>
    <p style="margin:4px 0 0;font-size:13px;color:#8b949e">{timeframe_descriptions[tf]}</p>
  </div>
  {cards}
</div>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Options Daily Briefing — {date_str}</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#c9d1d9;font-family:-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;font-size:14px;line-height:1.6}}
.hdr{{background:#161b22;border-bottom:1px solid #30363d;padding:16px 28px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}}
.hdr h1{{font-size:20px;font-weight:800;color:#58a6ff;letter-spacing:-0.5px}}
.hdr p{{font-size:11px;color:#8b949e;margin-top:2px}}
.nav{{display:flex;gap:8px}}
.nav a{{background:#21262d;color:#c9d1d9;text-decoration:none;padding:6px 16px;border-radius:6px;font-size:12px;font-weight:600;border:1px solid #30363d}}
.nav a:hover{{background:#30363d}}
.wrap{{max-width:1320px;margin:0 auto;padding:24px 20px 60px}}
img{{display:block;max-width:100%}}
</style>
</head>
<body>
<div class="hdr">
  <div>
    <h1>📈 Options Daily Briefing</h1>
    <p>AI-Powered Trade Analysis &mdash; {date_str} &mdash; Review before 9:00 AM ET</p>
  </div>
  <nav class="nav">
    <a href="#short">⚡ Short</a>
    <a href="#mid">📊 Mid</a>
    <a href="#long">🏔 Long</a>
  </nav>
</div>
<div class="wrap">
  {overview_html}
  {all_sections}
  <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px 16px;font-size:11px;color:#8b949e;margin-top:32px;line-height:1.7">
    ⚠️ <strong>Risk Disclosure:</strong> This briefing is for informational and educational purposes only. Options trading involves significant risk and is not suitable for all investors. Probability estimates use Black-Scholes models — actual outcomes may differ significantly. Always verify data against your broker before trading. Never risk more than you can afford to lose.
  </div>
</div>
</body>
</html>'''


# ─── Component helpers ────────────────────────────────────────────────────────

def trade_detail_box(label, value, color, sublabel='', small=False):
    val_size = '13px' if small else '18px'
    return f'''
    <div style="padding:14px 16px;border-right:1px solid #21262d;text-align:center">
      <div style="font-size:10px;font-weight:700;color:#8b949e;letter-spacing:1px;margin-bottom:4px">{label}</div>
      <div style="font-size:{val_size};font-weight:800;color:{color};line-height:1.2">{value}</div>
      {f'<div style="font-size:10px;color:#8b949e;margin-top:3px">{sublabel}</div>' if sublabel else ''}
    </div>'''

def greek_box(label, value, color):
    return f'''
    <div style="background:#0d1117;border-radius:8px;padding:10px;text-align:center;border:1px solid #21262d">
      <div style="font-size:10px;font-weight:700;color:#8b949e;margin-bottom:4px">{label}</div>
      <div style="font-size:16px;font-weight:800;color:{color}">{value:+.4f}</div>
    </div>'''

def prob_card(label, pct, color, sublabel):
    bar = f'<div style="background:#21262d;border-radius:4px;height:6px;margin:6px 0;overflow:hidden"><div style="background:{color};width:{pct}%;height:100%;border-radius:4px"></div></div>'
    return f'''
    <div style="text-align:center">
      <div style="font-size:10px;color:#8b949e;font-weight:700;letter-spacing:0.5px;margin-bottom:4px">{label}</div>
      <div style="font-size:22px;font-weight:800;color:{color}">{pct:.0f}%</div>
      {bar}
      <div style="font-size:10px;color:#8b949e">{sublabel}</div>
    </div>'''

def checklist_item(text):
    return f'<div style="display:flex;gap:6px;align-items:flex-start"><span style="color:#3fb950;flex-shrink:0">□</span><span>{text}</span></div>'
