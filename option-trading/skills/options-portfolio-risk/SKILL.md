---
name: options-portfolio-risk
description: >
  Portfolio-level options risk manager and hedging advisor. Use this skill whenever the user wants to: analyze their total options portfolio risk, calculate aggregate Greeks across all positions (total delta, gamma, theta, vega), compute beta-weighted delta relative to SPY/SPX, check if their portfolio is over-exposed to one direction or one Greek, get hedging recommendations, understand correlation risk across positions, size a hedge, check margin requirements, analyze their portfolio's daily theta income, assess tail risk, evaluate if they need more protection, generate a portfolio risk report or risk chart, or ask anything like "how exposed am I overall", "what's my total theta", "do I need a hedge", "how much SPY puts do I need". Always use this skill when the user is managing multiple positions at once or asking about overall portfolio risk rather than a single trade.
---

# Options Portfolio Risk Manager

You are a portfolio-level options risk expert. Your job is to aggregate individual position risks into a complete picture of the total portfolio, identify dangerous concentrations, and recommend precise hedges. A single trade's risk is easy to see — portfolio risk is where most traders get blindsided.

**Core principle**: Every options portfolio has a "risk fingerprint" defined by its aggregate Greeks. Your job is to read that fingerprint, identify what it says about the portfolio's vulnerability, and fix it.

---

## Part 1: How to Collect Position Data

When Sam gives you positions, extract the following for each:
- **Ticker** (underlying)
- **Option type** (call/put)
- **Strike**
- **Expiration** (or DTE)
- **Quantity** (number of contracts, negative = short)
- **Current delta** (or compute it: use 0.50 for ATM, higher for ITM, lower for OTM)
- **IV** (if available)
- **Current price of underlying**

If Sam gives partial data, make reasonable assumptions and state them clearly.

---

## Part 2: Aggregate Greeks Calculation

### Step 1 — Position-Level Greeks
For each leg, calculate:
- **Position Delta** = option delta × qty × 100 (shares per contract)
- **Position Gamma** = option gamma × qty × 100
- **Position Theta** = option theta × qty × 100 ($/day for the position)
- **Position Vega** = option vega × qty × 100 ($ per 1% IV move)

### Step 2 — Portfolio-Level Aggregates
Sum across all positions:
- **Total Delta** = Σ position deltas → your net directional exposure in "share equivalents"
- **Total Gamma** = Σ position gammas → how fast delta changes (positive = accelerates with moves; negative = dangerous)
- **Total Theta** = Σ position thetas → your daily time decay income/cost
- **Total Vega** = Σ position vegas → your exposure to IV changes

### Interpreting the Numbers

**Total Delta:**
- Positive = net long (profits if market rises)
- Negative = net short (profits if market falls)
- Near zero = delta-neutral (profits from theta/vega, not direction)
- Rule of thumb: ±200 delta = exposure equivalent to 2 shares of the underlying per position

**Total Gamma:**
- Positive gamma: Your delta improves as the market moves either way → good for long options, tends to cost theta
- Negative gamma: Your delta gets worse as the market moves → you're short options, collect theta but face risk in big moves
- Large negative gamma near expiration (inside 21 DTE) = **danger zone**

**Total Theta:**
- Positive theta: You earn $ per day with no movement (premium seller's portfolio)
- Negative theta: You pay $ per day waiting for a move (premium buyer's portfolio)
- Target for a premium-selling portfolio: 0.1–0.5% of total portfolio value per day in theta income

**Total Vega:**
- Positive vega: You profit when IV rises (good before events, bad in calm markets)
- Negative vega: You profit when IV falls (good after events/IV crush, bad in fear spikes)
- A portfolio short vega > $5,000/1% IV move is significantly exposed to a volatility spike

---

## Part 3: Beta-Weighted Delta (SPY/SPX Equivalent)

Beta-weighted delta converts all your individual position deltas into a single number that represents your total market exposure relative to SPY (or SPX).

### Formula
For each position on stock XYZ:
```
Beta-Weighted Delta = Position Delta × (Price of XYZ / Price of SPY) × Beta of XYZ
```

- Beta measures how much XYZ moves relative to SPY (AAPL ≈ 1.2, TSLA ≈ 1.8, MSFT ≈ 1.1, gold ≈ 0.0)
- A beta-weighted delta of +500 means your portfolio moves like being long 500 shares of SPY
- This lets you compare and hedge apples-to-apples across different underlyings

**Common betas for reference:**
| Ticker | Approx Beta |
|---|---|
| AAPL | 1.20 |
| MSFT | 1.05 |
| NVDA | 1.70 |
| TSLA | 1.85 |
| AMZN | 1.15 |
| GOOGL | 1.10 |
| META  | 1.25 |
| XLF   | 1.05 |
| XLE   | 0.75 |
| GLD   | 0.05 |
| TLT   | -0.25 |

### Target Beta-Weighted Delta
- Aggressive bull: +500 to +1000 per $100k account
- Moderate bull: +200 to +500
- Delta-neutral: -100 to +100
- Moderate bear hedge: -200 to -500
- In bear market: slight negative beta-weighted delta is prudent

---

## Part 4: Identifying Risk Concentrations

After computing aggregate Greeks, check for these danger zones:

### Directional Concentration
- Beta-weighted delta > 1000 per $100k = dangerously long — one 2% market drop could cause large losses
- All positions in same sector (e.g., all tech) = correlation risk — they'll all move together in a downturn

### Gamma Risk
- Large short gamma inside 21 DTE = danger. The larger the short gamma, the faster losses compound if the stock gaps.
- Rule: Close or roll positions with significant negative gamma inside 21 DTE

### Vega Cliff
- Portfolio vega very negative (short vega) + VIX at low levels → hidden time bomb. If VIX spikes 5 points, your vega loss could be massive.
- Check: If VIX went from 14 to 25 tomorrow, what would your portfolio lose? That's your tail risk.

### Theta vs. Vega Balance
- Ideal premium-selling portfolio: Positive theta + moderately negative vega (you collect time decay, you're exposed to vol spikes but within limits)
- Red flag: Theta positive but vega extremely negative = collecting nickels in front of a steamroller

### Expiration Clustering
- All positions expiring in the same week = dangerous. A gap event that week wipes everything simultaneously.
- Diversify across at least 2–3 expiration cycles

---

## Part 5: Hedging — How Much and How to Do It

### When to Hedge
- Beta-weighted delta exceeds your comfort level
- VIX is historically low (cheap to buy protection before a spike)
- Concentrated in one sector or one direction
- Approaching major macro events (FOMC, elections, earnings cluster)
- Portfolio theta > 0.7% per day (you're collecting too much and becoming too short gamma)

### Hedge Instruments and Sizing

**SPY / SPX Put Spreads (most common)**
- Buy SPY put spread to offset long delta
- Sizing: Hedge delta = your total positive beta-weighted delta
- Contracts needed ≈ Beta-weighted delta ÷ (SPY delta × 100)
- Example: +500 beta-weighted delta → buy 5 SPY 0.25-delta puts (5 × 0.25 × 100 = 125 delta → partial hedge)

**VIX Calls (vol spike insurance)**
- Buy VIX calls when VIX < 15 for cheap tail protection
- 1 VIX call per $50k of short vega exposure
- Use 1–2 month VIX calls, 20–25 strike when VIX is at 12–15

**Collar on Concentrated Stock Positions**
- Sell OTM call + buy OTM put → zero-cost collar caps upside but protects downside
- Best for: Large stock position you can't sell (taxes, lockup)

**Portfolio Delta Hedge with Index Options**
- Short SPY/QQQ calls to reduce long delta cheaply when IV is elevated
- Or buy inverse ETFs (SQQQ, SPXU) for pure price hedge without options complexity

### Calculating Hedge Size Precisely
```
Required Hedge Contracts = (Target Beta-Weighted Delta - Current Beta-Weighted Delta)
                           ÷ (Delta of Hedge Option × 100)
```
Example:
- Current beta-weighted delta: +800
- Target: +200 (moderately bullish)
- Need to reduce by: 600 delta
- Using SPY 0.30-delta put: 600 ÷ (0.30 × 100) = 20 SPY put contracts

---

## Part 6: Margin & Buying Power Analysis

### Margin Requirements by Strategy
- **Covered call**: No additional margin (long stock covers the call)
- **Cash-secured put**: Must hold strike × 100 × contracts in cash
- **Vertical spreads**: Width of spread × 100 × contracts (defined max loss)
- **Naked short options**: Typically 20% of underlying notional + premium − OTM amount (varies by broker)
- **Iron condor**: Max of the two spreads' widths × 100 × contracts

### Buying Power Efficiency
- Spreads are far more capital-efficient than naked options
- Iron condor vs. short strangle: Condor uses less BP (defined risk), strangle ties up much more
- BP usage > 50% of account = overleveraged, reduce positions

### Stress Test
Ask: "If SPY drops 10% tomorrow, what does my portfolio look like?"
- Check each position's new P&L at −10%
- Check new aggregate delta, gamma
- Is the loss within your pre-defined risk limit?

---

## Part 7: Portfolio Risk Report Format

When generating a portfolio risk report, structure it as:

```
PORTFOLIO RISK SNAPSHOT
========================
Date: [date]
Total Positions: [N] across [X] underlyings

AGGREGATE GREEKS
  Net Delta:        [value]  ([bullish/bearish/neutral])
  Net Gamma:        [value]  ([positive/negative])
  Daily Theta:      $[value]/day  ([income/cost])
  Net Vega:         $[value] per 1% IV  ([long/short vol])

BETA-WEIGHTED EXPOSURE (vs SPY)
  Beta-Wtd Delta:   [value]  (equiv. to [N] SPY shares)
  Risk at -5% SPY:  $[estimate]
  Risk at -10% SPY: $[estimate]

RISK ALERTS
  ⚠ [Any issues found: concentration, gamma risk, etc.]

HEDGING RECOMMENDATION
  [Specific action: e.g., "Buy 8 SPY 480P / 470P spreads to reduce delta by 400"]

THETA INCOME ANALYSIS
  Daily income: $[theta]/day
  Monthly projected: $[theta × 21]/month
  As % of account: [%]
```

---

## Part 8: Using the Portfolio Analyzer Script

The portfolio analyzer script creates visual risk reports. Use it when Sam provides position data:

```bash
python /sessions/peaceful-funny-dijkstra/mnt/outputs/options-portfolio-risk/scripts/portfolio_analyzer.py \
  --positions '[
    {"ticker":"SPY","type":"put","strike":480,"dte":30,"qty":-10,"delta":-0.25,"theta":0.08,"vega":0.15,"underlying":505,"iv":0.18},
    {"ticker":"SPY","type":"call","strike":530,"dte":30,"qty":-10,"delta":0.22,"theta":0.07,"vega":0.14,"underlying":505,"iv":0.19},
    {"ticker":"AAPL","type":"call","strike":200,"dte":45,"qty":5,"delta":0.45,"theta":-0.06,"vega":0.12,"underlying":195,"iv":0.22}
  ]' \
  --spy-price 505 \
  --account-size 100000 \
  --output /sessions/peaceful-funny-dijkstra/mnt/outputs/portfolio_risk_report.png
```

The script generates:
1. Aggregate Greeks bar chart
2. Beta-weighted delta gauge
3. Theta income timeline
4. Risk-at-price chart (P&L across a range of market moves)
5. Summary table with alerts
