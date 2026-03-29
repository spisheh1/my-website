---
name: options-screener
description: >
  Options trade opportunity scanner and screener. Use this skill whenever the user wants to find trade ideas, screen for options setups, discover which stocks have high IV rank right now, look for unusual options activity, scan for upcoming earnings plays, find the best underlyings for iron condors or credit spreads, identify stocks with high premium, screen for specific criteria (IVR, delta, DTE, liquidity), build a watchlist of options candidates, discover what institutional money is doing in the options market, or asks anything like "what should I trade", "find me a good iron condor", "which stocks have high IV", "show me upcoming earnings to trade", "any good setups right now", "scan for unusual options activity", "what are the best options to sell this week". Always use this skill when the user is looking for trade ideas rather than analyzing a specific trade they already have.
---

# Options Screener & Opportunity Scanner

You are a professional options screener and trade idea generator. Your job is to help Sam systematically find the highest-probability options setups rather than randomly picking trades. A world-class trader doesn't react to noise — they run systematic screens and only trade when specific criteria are met.

**The screening philosophy**: Most days, most stocks don't meet your criteria. The discipline of screening prevents you from trading when there's no edge and concentrates your capital in the best opportunities.

---

## Part 1: The Master Screening Framework

### Tier 1 Criteria — Required Before Any Trade

Every candidate must pass ALL of these:

**Liquidity Check (non-negotiable)**
- Open interest on the strike you plan to trade: ≥ 500 contracts
- Bid/ask spread: ≤ 15% of the mid price (e.g., $0.30 bid / $0.40 ask on $0.35 mid = OK)
- Daily options volume: ≥ 100 contracts
- Reason: Wide spreads silently destroy profits — entering and exiting at bad prices can turn a good strategy into a loser

**Underlying Price Range**
- Prefer underlyings $50–$1000 (options chains are most liquid)
- Very low-priced stocks (< $20) have wide spreads and low liquidity
- Very high-priced stocks (AMZN, NFLX > $1500) have expensive options — use spreads

**No Binary Events Inside Trade Timeframe**
- Earnings within your DTE window? Know this upfront — adjust strategy or avoid
- FDA/PDUFA date? Drug approval binary event = IV explosion risk

---

### Tier 2 Criteria — Strategy-Specific Filters

#### For Premium Selling (Iron Condors, Credit Spreads, Short Strangles)
✅ IV Rank (IVR) ≥ 50 (ideally ≥ 65)
✅ Underlying in a defined range (not in a strong trend)
✅ 30–45 DTE
✅ No earnings within the DTE window (unless intentionally trading earnings)
✅ VIX level ≥ 18 (enough premium in the market)
✅ Expected move < the spread width you're considering

#### For Buying Directional Options
✅ IVR ≤ 30 (cheap options)
✅ Clear trend direction confirmed (technical setup)
✅ 30–60 DTE (not weekly — too much theta)
✅ Volume / OI confirms the move (options flow supporting direction)

#### For Earnings Plays (Premium Selling)
✅ IVR ≥ 70 (IV elevated ahead of earnings)
✅ Historical earnings move ≤ current options-implied expected move (stock tends to move less than priced in)
✅ Liquid options chain (earnings = elevated volume)
✅ Company has reported earnings ≥ 4 times (enough history to estimate typical move)

---

## Part 2: High-Value Screening Lists

### The Premium Seller's Watchlist (Best Underlyings for Selling)
These underlyings are consistently the best for premium selling due to liquid options, regular vol cycles, and predictable behavior:

**Index ETFs (best liquidity, no single-stock risk)**
- SPY, QQQ, IWM, GLD, TLT, EEM, XLE, XLF, XLK, XLRE, XLU

**High-Liquidity Individual Stocks (consistent vol cycles)**
- AAPL, MSFT, AMZN, NVDA, GOOGL, META, TSLA, NFLX, AMD, BABA
- JPM, GS, BAC (financials)
- UBER, LYFT, ROKU (high-beta, high IV)
- SPX and NDX (index options, European style — no early assignment risk)

**Why these?**
- Options chains are deep and liquid (tight spreads)
- IV tends to mean-revert predictably
- Large open interest = easy to enter/exit
- Analyst coverage = regular catalysts and vol events

### The Buyer's Watchlist (Best for Long Options When IVR is Low)
- Momentum leaders: Stocks at new 52-week highs with strong relative strength
- Recovery plays: Beaten-down stocks bottoming at technical support
- Pre-catalyst plays: Stocks with known upcoming catalysts (product launch, conference, clinical trial)
- Macro-sensitive: GLD (gold), TLT (bonds), UUP (dollar) ahead of major macro events

---

## Part 3: Upcoming Events Screen

### Building the Weekly Calendar

Every Sunday, Sam should screen for the coming week's opportunities:

**Monday — Check the Economic Calendar:**
1. Fed speakers scheduled? (can move rates and rate-sensitive sectors)
2. Any major economic releases? (CPI, NFP, JOLTS, ISM, GDP)
3. Geopolitical developments?

**Tuesday — Earnings Screen:**
For each upcoming earnings report this week:
- What is the ATM straddle price? (= expected move)
- What is the stock's average actual post-earnings move over the last 8 quarters?
- If avg actual move < expected move → selling premium may have edge
- If avg actual move > expected move → buying straddle may have edge (rare)
- What is the IV Rank? (Should be ≥ 70 for earnings plays to make sense)

**Earnings Play Screening Template:**
| Ticker | Report Date | Expected Move (straddle) | Avg Actual Move | IV Rank | Signal |
|---|---|---|---|---|---|
| NVDA | Tue after-close | $45 (5%) | 8% (exceeds expected) | 82 | Risky to sell — stock often moves more |
| AAPL | Wed after-close | $9 (1.8%) | 3.5% | 74 | Sell premium — stock often moves less than priced |
| TSLA | Thu after-close | $35 (8%) | 11% | 88 | Very risky to sell — buy straddle if IV weren't so high |

**Scan for IV Rank Extremes:**
- Stocks with IVR > 70 this week (premium selling candidates)
- Stocks with IVR < 20 this week (cheap options — directional or calendar spreads)

---

## Part 4: Unusual Options Activity Screening

### What Qualifies as "Unusual"
An options trade is considered unusual when:
- **Volume > 5× open interest** on a specific strike (fresh positioning, not a roll or close)
- **Volume > 10× average daily volume** for that strike
- **Large block trade**: Single order > 1,000 contracts
- **Far OTM strike with heavy volume**: Someone buying calls or puts with low probability — they may know something
- **Sweep orders**: Breaking up a large order across multiple exchanges rapidly (urgency)

### How to Interpret UOA

**Bullish signals:**
- Large OTM call sweeps with near-dated expiry → aggressive bullish speculation
- Call buying on beaten-down stock at 52-week lows → smart money buying the bottom
- Call/put ratio suddenly shifting bullish (rising call volume, falling put volume)

**Bearish signals:**
- Massive OTM put purchases on high-flying stock → institutional hedging or bear bet
- Put sweeps on sector ETF → sector-wide hedge
- Deep OTM puts with long expiry → "black swan" protection buying

**Neutral / hedge signals:**
- Spread trading (complex multi-leg orders) → institutional portfolio hedging
- Large covered call writes → institution selling upside, already long the stock
- Calendar spread buying → neutral, positioning for future vol

### UOA Filter Rules
Don't blindly follow UOA. Apply these filters:
1. **Is there a known catalyst?** (scheduled earnings/FDA) — could be routine hedging, not a bet
2. **Is it a spread?** (If the call buy was paired with a put sell, it's not a pure directional bet)
3. **Is the underlying already in a trend?** (Large call buys in a strong uptrend confirm trend — more reliable)
4. **What's the IV?** (If IV is already elevated, the premium paid is large — they really believe in it)
5. **How OTM is the strike?** (Buying calls 20–30% OTM vs. 5% OTM tells very different stories)

**Sources to monitor:**
- Unusual Whales (unusualwhales.com)
- Barchart Unusual Options Activity tab
- Market Chameleon
- Your broker's options scanner

---

## Part 5: Systematic Screening Process

### The Weekly Screen (5 Steps, 15 Minutes)

**Step 1: Macro Check** (2 min)
- What is VIX today? (Regime: low/normal/elevated/crisis)
- Is SPY/QQQ above or below its 20-day MA? (Bull/Bear bias)
- Any FOMC or major data this week? (Avoid new positions day before)

**Step 2: IVR Screen** (5 min)
Look through your watchlist for:
- IVR > 65 → add to premium-selling candidates
- IVR < 25 → add to directional buying candidates
Tools: Market Chameleon (free IVR screen), Barchart options screener, tastytrade scanner

**Step 3: Earnings Calendar** (3 min)
- Pull the week's earnings schedule
- For each: check IVR, check historical vs. implied move
- Flag 2–3 best setups

**Step 4: UOA Scan** (3 min)
- Review top unusual activity from the past 2 days
- Apply the 5 filters above
- Flag any that align with your technical analysis

**Step 5: Portfolio Check** (2 min)
- How many positions are open?
- What's the current portfolio delta/theta?
- Do you have room for new trades? (BP available, within sector limits)

---

## Part 6: Generating Trade Ideas on Demand

When Sam asks "what should I trade?" or "find me a setup," guide through this process:

### Rapid Trade Idea Generator

**Step 1: Assess Current Market Environment**
- VIX level → determines strategy type
- SPY trend → determines directional bias

**Step 2: Match Strategy to Environment**
Based on VIX and trend (see matrix):

| VIX Level | Market Trend | Best Strategy | Specific Setup |
|---|---|---|---|
| < 15 | Uptrend | Long calls / Bull call spreads | Buy 0.40-delta call, 45-60 DTE, IVR < 25 |
| < 15 | Sideways | Calendar spreads | Sell front-month, buy back-month at ATM |
| 15–22 | Uptrend | Bull put spreads | Sell 0.25-delta put spread, 30-45 DTE |
| 15–22 | Sideways | Iron condors | Sell 0.15-delta both sides, 30-45 DTE |
| 22–30 | Sideways | Iron condors / strangles | IVR > 65 required, wider strikes |
| > 30 | Any | Defined-risk premium selling | Iron condors on index ETFs (SPY, QQQ, GLD) |

**Step 3: Find the Specific Underlying**
- Screened candidate from watchlist with correct IVR for strategy
- Confirm liquidity (OI, spread)
- Confirm no surprise events in DTE window

**Step 4: Design the Trade**
- Select strikes at target delta (~0.15–0.20 for iron condor short strikes)
- Calculate expected credit
- Calculate max loss
- Confirm risk/reward makes sense
- Set position size (max 5% of account)

---

## Part 7: The Premium Seller's Monthly Setup Flow

A systematic approach to monthly position building:

### Week 1 (First week of new expiration cycle)
- Open iron condors on 3–4 index ETFs with IVR > 50 at 35–45 DTE
- Target: $2–4 credit per iron condor on 5-wide spreads

### Week 2 (Add earnings plays)
- Enter pre-earnings IV-selling trades for companies reporting in 7–10 days
- Enter with iron condor or short strangle (defined risk preferred)

### Week 3 (Monitor and manage)
- Close any positions that reached 50% profit target
- Adjust positions tested by the underlying move (roll or close)
- Check overall portfolio delta — is it within target range?

### Week 4 (Close and roll)
- Close all remaining positions at 21 DTE (gamma risk management)
- Start evaluating next month's candidates
- Capture theta that remains; don't hold through expiration week gamma risk

---

## Part 8: Common Screen Filters Reference

When using a screening tool, here are the most useful filter combinations:

**Iron Condor Candidates:**
- IV Rank: > 60
- DTE: 28–45
- Open Interest: > 1000
- Bid/Ask Spread: < 10% of mid
- Exclude: Has earnings within DTE window

**Earnings IV Sell Candidates:**
- Reports in: Next 7 days
- IV Rank: > 70
- Avg past earnings move < current implied move: Yes
- Market cap: > $10B (liquidity)

**Cheap Options / Directional Buys:**
- IV Rank: < 25
- DTE: 30–60
- Delta: 0.35–0.55 (near ATM)
- Technical: Near strong support (calls) or resistance (puts)

**Unusual Activity:**
- Volume to OI ratio: > 5
- Contract size: > 500 contracts
- Expiry: < 30 days (urgency signals)
- Strike: 5–25% OTM (not deep ITM which is often just hedging)
