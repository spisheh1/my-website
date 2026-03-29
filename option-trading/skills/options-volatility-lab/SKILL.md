---
name: options-volatility-lab
description: >
  Advanced volatility analysis lab for options traders. Use this skill whenever the user asks about: implied volatility (IV) in depth, IV rank or percentile, the volatility term structure (near vs. far month IV), contango vs. backwardation in volatility, the volatility surface, put/call skew analysis, volatility risk premium (VRP — the gap between IV and realized vol), historical vs implied volatility comparison, VIX analysis or VIX term structure (VIX vs VIX3M vs VIX9D), vol regime detection (low/normal/high/crisis), IV mean reversion signals, how to trade volatility itself (VIX products, UVXY, SVXY), calendar spreads based on term structure, whether options are cheap or expensive right now, vol crush timing, or any question containing words like "volatility", "IV", "VIX", "vol surface", "skew", "term structure", "contango", "backwardation", "realized vol", "historical vol", "VRP". This skill provides deeper volatility intelligence than the main options-trading-mastery skill.
---

# Options Volatility Lab — Advanced Volatility Intelligence

You are a volatility specialist. While most traders think in terms of direction (up or down), expert options traders think primarily in volatility space. Volatility is its own asset class with its own dynamics, mean-reversion properties, and tradeable structures. This skill gives you deep mastery of all of it.

**The volatility trader's edge**: Most retail options traders focus on direction. The structural edge in options markets comes from understanding volatility — specifically, that IV consistently overestimates actual realized movement (the Volatility Risk Premium), and that IV is mean-reverting and exploitable.

---

## Part 1: The Volatility Hierarchy

### Implied Volatility (IV)
- Derived from option market prices via Black-Scholes
- Forward-looking: what the market *expects* volatility to be over the option's life
- Always expressed as annualized standard deviation (25% IV = market expects stock to move ~25% in a year)
- **Daily expected move**: Stock Price × IV ÷ √252 (e.g., $500 × 0.20 ÷ √252 ≈ $6.30/day)
- **Weekly expected move**: Stock Price × IV ÷ √52
- **Event expected move**: Stock Price × IV × √(DTE/365)

### Historical/Realized Volatility (HV/RV)
- Calculated from past actual price movements (typically 20-day, 30-day, or 60-day windows)
- Backward-looking: what volatility actually was
- Formula: Annualized standard deviation of daily log returns

### The VRP (Volatility Risk Premium)
- VRP = IV − RV (implied minus realized)
- Historically, VRP has been positive on average: IV overestimates RV by ~2–4 points
- This is the structural edge for premium sellers — the market consistently overpays for options
- When VRP is large (IV >> RV): Strong sell-premium signal
- When VRP is small or negative (IV ≤ RV): Rare, but signals options are cheap or something unusual is expected

### IV Percentile vs. IV Rank
- **IV Rank (IVR)**: Position within 52-week high/low range — most common
  - IVR = (Current IV − 52w Low) / (52w High − 52w Low) × 100
- **IV Percentile (IVP)**: % of days in past year where IV was lower
  - IVP 85 = IV is higher than 85% of all days in the past year
- IVP is generally more informative than IVR for thinly-traded stocks
- Use either: IVR/IVP > 70 = sell premium; < 30 = buy options

---

## Part 2: The Volatility Term Structure

### What It Is
The term structure shows IV across different expiration dates for the same underlying. Plot DTE on the X-axis and IV on the Y-axis to see the "vol curve."

### Contango (Normal State)
- Near-term IV < Far-term IV
- The market prices more uncertainty for events further out in time
- Example: 30-day IV = 20%, 60-day IV = 23%, 90-day IV = 25%
- **Trading implication**: Calendar spreads (sell near, buy far) tend to work well in contango — you sell cheaper near-term IV while holding longer-dated vol

### Backwardation (Inverted/Fear State)
- Near-term IV > Far-term IV
- Happens during fear, events, or market dislocations
- Example: 30-day IV = 42%, 60-day IV = 35%, 90-day IV = 30%
- **Trading implication**: Calendar spreads don't work in backwardation (near-term IV collapses the most as fear fades). Instead, sell short-dated straddles/strangles to capture the high near-term premium.

### Reading the Term Structure Slope
- **Steep contango** (term structure sloping sharply up): Market expects future event. Near-term is calm.
- **Flat term structure**: Market doesn't see near vs. far difference in uncertainty — neutral signal.
- **Inverted (backwardation)**: Fear is concentrated in the near term — a current event is the driver.

### VIX Term Structure
The VIX itself has a term structure:
- **VIX (30-day SPX IV)**: Standard fear gauge
- **VIX3M (93-day SPX IV)**: Longer-dated market expectations
- **VIX9D (9-day IV)**: Very short-dated fear
- **VXST-VIX ratio** (9-day vs 30-day): Ratio > 1 = front-end fear spike, temporary; Ratio < 0.85 = complacency
- **VIX-VIX3M spread**: When VIX > VIX3M (backwardation), sell the VIX mean-reversion: iron condors on SPX, short UVXY, etc.

---

## Part 3: The Volatility Surface

### What It Is
The volatility surface is a 3D representation of IV across:
- **X-axis**: Strike prices (or delta)
- **Y-axis**: Expiration dates (DTE)
- **Z-axis**: Implied volatility

It tells you the full pricing structure of every option in the chain at a glance.

### Key Surface Features

**The Skew (Volatility Smile)**
- Looking across strikes at a single expiration
- **Put skew**: Lower strikes (OTM puts) have higher IV than higher strikes (OTM calls)
- This is structural and persistent — demand for downside protection inflates put premiums
- Skew steepness = how much more OTM puts cost relative to OTM calls
- Steep skew → consider risk reversals (sell put, buy call at no cost or small credit)
- Flat skew → consider straddles (put and call roughly equally priced)

**The Wing Premium**
- Very OTM options (> 2 standard deviations away) often have higher IV than model predicts
- "Fat tails" — the market prices in more large-move probability than BS assumes
- This creates opportunity: Sell the wings (iron condors with wide strikes) when wing IV is very elevated

**Term Structure Interaction with Skew**
- In normal markets: skew is steeper for near-dated expirations (more put demand for near-term protection)
- During events: near-term skew flattens or inverts (market fears moves in either direction)

---

## Part 4: Vol Regime Detection

### The 4 Volatility Regimes

**Regime 1: Low Volatility (VIX < 15, IVR < 25)**
- Characteristics: Trending up, low fear, complacency
- Options pricing: Cheap, underpricing realized moves often
- What works: Directional long options (cheap premium), calendar spreads, long gamma
- What doesn't: Selling premium has low edge — not enough premium to justify the risk

**Regime 2: Normal Volatility (VIX 15–22, IVR 30–60)**
- Characteristics: Normal market function, some two-way risk
- Options pricing: Fairly valued
- What works: Iron condors, credit spreads, covered calls — the "steady state" for premium sellers
- What doesn't: Nothing particularly broken; this is the sweet spot

**Regime 3: Elevated Volatility (VIX 22–30, IVR 60–80)**
- Characteristics: Market worried, choppy, event-driven
- Options pricing: Expensive, IV likely to mean-revert
- What works: Premium selling is very attractive — large credit available
- What doesn't: Buying options is expensive; directional plays cost more

**Regime 4: Crisis Volatility (VIX > 30, IVR > 80)**
- Characteristics: Fear, sharp downtrend, correlation spike (everything moves together)
- Options pricing: Very expensive, often irrational
- What works: Sell premium with DEFINED RISK (iron condors, not naked straddles). VIX mean-reversion almost certain.
- What doesn't: Long options burn fast as IV collapses even if the move continues; adding short delta risk is dangerous

### Regime Transition Signals
- VIX breaking above its 20-day MA: vol regime shifting higher — reduce short premium exposure
- VIX/VIX3M ratio > 1.10: short-term fear spike, typically temporary
- RV/IV ratio rising above 1.0: realized moves exceeding implied — bad for premium sellers
- VIX closing below 15-day MA after a spike: regime normalizing — add premium selling exposure

---

## Part 5: Volatility Mean Reversion — Timing the Trade

### Why IV Mean-Reverts
IV cannot stay elevated forever — the underlying fear/uncertainty resolves. Historical studies show:
- Average VIX spike takes 15–30 trading days to revert to pre-spike levels
- After VIX exceeds 30, the probability of it being lower 30 days later is ~80%
- The higher the spike, the faster the reversion (extreme fear is self-limiting)

### Mean Reversion Trading Signals

**Buy signal for premium selling** (signals IV will fall):
- VIX > 25 AND declining after a spike peak
- IVR > 75 on the underlying AND the news catalyst has passed
- IV/HV ratio > 1.5 (IV is 50% above actual recent moves)

**Avoid premium selling** (signals IV may rise further):
- VIX breaking out to new highs (trending higher, not spiking)
- IVR rising week-over-week (IV is expanding, not contracting)
- Ongoing unresolved macro event (active geopolitical crisis, Fed in tightening cycle)

### The Mean Reversion Trade
When IV is elevated with a high probability of mean reversion:
1. Sell an iron condor or short strangle on the underlying with high IVR
2. Select 30–45 DTE
3. Exit at 50% of max profit (when IV has fallen ~halfway back)
4. The edge: you collected premium at inflated IV levels, exited when IV was lower = you captured the VRP

---

## Part 6: Trading Volatility Directly (VIX Products)

### VIX-Linked ETPs
- **UVXY / VIXY**: Long VIX futures (2× leveraged for UVXY). Hedges against vol spikes. Decays in contango markets.
- **SVXY**: Short VIX futures (inverse). Benefits from vol decay. Catastrophic in vol spikes.
- **VXX**: 1× long VIX futures. Similar to UVXY but unlevered.

### Key Property: VIX Futures Roll Decay
In contango (normal state), VIX futures must roll from cheaper near-term to more expensive far-term contracts every month. This causes daily "roll decay" that erodes long VIX products ~3–5% per month in calm markets. UVXY loses money consistently in low-vol environments.

**Practical applications:**
- Buy UVXY/VXX calls when VIX is very low (< 13) as cheap tail insurance
- Short UVXY (or buy SVXY) as a systematic carry strategy when VIX is in contango — BUT this can be catastrophic in a vol spike (use defined risk structures, not outright shorts)

### VIX Options
- VIX options are European-style (settle to VIX on expiration, not tradeable)
- VIX options price off VIX *futures*, not VIX spot — check the relevant futures level
- Best uses:
  - Buy VIX calls as portfolio insurance during low-vol periods (very cheap when VIX < 14)
  - Sell VIX put spreads to collect premium after a spike (VIX mean-reversion bet)

### Term Structure Carry Trade
The VIX futures curve in contango provides a structural carry opportunity:
- Short front-month VIX futures, long back-month VIX futures → profit from the roll as front-month decays
- This is essentially what VXX/UVXY do in reverse — short these ETPs systematically
- Risk: A sudden vol spike wipes out many months of carry in days. **Always use defined risk.**

---

## Part 7: Volatility Analysis Outputs

### When Sam Provides IV/Vol Data

Use the chart generator from options-chart-analysis to create:

1. **IV History chart** with IVR badge and buy/sell signal
2. **Term structure chart** (plot IV vs DTE for multiple expirations)
3. **IV Smile/Skew chart** across strikes

### Volatility Analysis Report Format

When performing a full volatility analysis on a stock/index:
```
VOLATILITY ANALYSIS REPORT: [TICKER]
======================================
Current IV (30-day):      [X]%
Realized Vol (30-day):    [X]%
VRP (IV − RV):            [X]% → [Sell premium / Buy options / Neutral]

IV RANK/PERCENTILE
  52-week High IV:        [X]%
  52-week Low IV:         [X]%
  IV Rank:                [X] → [Elevated/Normal/Low]
  IV Percentile:          [X]%

TERM STRUCTURE
  Near-term (30d):        [X]%
  Mid-term (60d):         [X]%
  Long-term (90d+):       [X]%
  Structure:              [Contango/Backwardation/Flat]
  Slope:                  [Steep/Normal/Flat]

SKEW
  ATM IV:                 [X]%
  25-delta Put IV:        [X]%
  25-delta Call IV:       [X]%
  Put Skew:               [X]% → [High/Normal/Low]

VOL REGIME:               [Low/Normal/Elevated/Crisis]
SIGNAL:                   [SELL PREMIUM / BUY OPTIONS / NEUTRAL]

RECOMMENDED STRATEGY:
  [Specific strategy with rationale based on vol analysis]
```

---

## Part 8: Volatility Arbitrage Concepts (Advanced)

### Realized vs. Implied Arbitrage
- If you believe realized vol will exceed IV → buy straddles (long gamma, long vega)
- If you believe RV will be below IV → sell straddles/strangles (short gamma, short vega, positive theta)
- The decision requires a volatility forecast, not just a price forecast

### Dispersion Trading
- Buying single-stock vol while selling index vol (or vice versa)
- Index IV < sum of component IVs → sell index straddle, buy component straddles
- Profits when stocks move independently (high dispersion), loses when they move together (low dispersion / crisis)
- Very capital-intensive, institutional-level strategy

### Calendar Spread Vol Trading
- Buy a calendar spread when near-term IV is depressed relative to far-term (steep contango)
- Profit from: near-term IV rising, near-term theta decay, or convergence of the term structure
- The "dream scenario": near-term IV rises temporarily, you sell the near-term at elevated IV, and the far-term leg retains its value
