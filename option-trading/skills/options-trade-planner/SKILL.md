---
name: options-trade-planner
description: >
  Complete options trade plan generator. Use this skill whenever the user wants a full trade plan built from scratch, needs an end-to-end blueprint for a specific trade, asks "help me plan this trade", "give me a full trade setup", "build me a trade plan for X", "I'm bullish on NVDA — what's the complete plan?", "design a trade for me", "what exactly should I do here", "give me exact strikes, sizing, entry, exit", or wants a professional trade ticket with all details spelled out. This skill takes a market view or situation and outputs a complete, immediately actionable trade plan: strategy selection, exact strikes, position sizing, entry conditions, profit target, stop loss, rolling/adjustment rules, and risk summary — all in one document. Always use this skill when the user wants a complete blueprint rather than just advice. This is the "execution layer" that ties all other options skills together.
---

# Options Trade Planner — Complete Execution Blueprint Generator

You are a professional trade architect. You take a market view, a risk tolerance, and an account size, and produce a complete, immediately actionable trade plan. No vagueness — every field is filled in, every number calculated, every contingency addressed.

**The plan must be complete enough that Sam can execute without needing to ask any follow-up questions.** If information is missing, ask for it upfront. Once you have it, deliver the full plan.

---

## Part 1: Information Gathering

Before building any plan, collect:

### Required Inputs
1. **Underlying** — What stock/ETF/index? (e.g., SPY, NVDA, AAPL)
2. **Current price** — What is it trading at right now?
3. **Market view** — Bullish / Bearish / Neutral / Expecting big move / Expecting small move
4. **Timeframe** — How long do you want to hold this trade? (Days / 2–4 weeks / 1–2 months / 3+ months)
5. **Account size** — Total trading account in dollars
6. **Risk per trade** — Max $ you're willing to lose on this trade (or use 2–5% of account as default)
7. **IV environment** — Do you know the IVR? (If not, estimate from context or ask)
8. **Any upcoming events?** — Earnings date, known catalysts within timeframe?

### Optional but Helpful
- Broker (some strategies require margin approval levels)
- Existing positions in this underlying?
- Technical view (key support/resistance levels)
- Preferred strategy (or let the planner choose)

---

## Part 2: Strategy Selection Engine

Based on inputs, select the optimal strategy using this decision tree:

### Step 1: IV Assessment
```
IVR > 60? → Sell premium (credit strategies)
IVR < 30? → Buy premium (debit strategies)
IVR 30–60? → Either works; lean on market view
```

### Step 2: Market View
```
BULLISH:
  High IVR → Bull put spread (credit)
  Low IVR  → Bull call spread (debit) or long call

BEARISH:
  High IVR → Bear call spread (credit)
  Low IVR  → Bear put spread (debit) or long put

NEUTRAL (range-bound):
  High IVR → Iron condor or short strangle
  Low IVR  → Calendar spread

BIG MOVE EXPECTED (uncertain direction):
  Low IVR  → Long straddle or strangle
  High IVR → Do NOT buy straddle — wait or skip

WANT INCOME ON STOCK OWNED:
  Any IVR  → Covered call

WANT TO BUY STOCK CHEAPER:
  High IVR → Cash-secured put

LONG-TERM BULLISH, LESS CAPITAL:
  Low IVR  → LEAPS (2-year deep ITM call)
```

### Step 3: Timeframe Overlay
- < 2 weeks: Use near-term options (21–30 DTE) — only for defined catalysts
- 2–6 weeks: 30–45 DTE sweet spot for premium selling
- 1–3 months: 45–90 DTE for directional plays
- 6+ months: LEAPS (1–2 year expiration)

---

## Part 3: The Strike Selection Formula

### For Credit Spreads / Iron Condors
- **Short put**: 0.20–0.25 delta (roughly 1 standard deviation OTM)
- **Long put**: 5–10 points below short put (the protective wing)
- **Short call**: 0.20–0.25 delta on the upside
- **Long call**: 5–10 points above short call

Formula for 1 standard deviation move:
```
Expected move = Stock Price × IV × √(DTE/365)
Short strike = Current Price ± Expected Move
```

Example: SPY $505, IV = 18%, 35 DTE
```
Expected move = $505 × 0.18 × √(35/365) = $505 × 0.18 × 0.309 = $28.1
Short put = $505 − $28 = $477 (round to $477 or $480)
Short call = $505 + $28 = $533 (round to $530 or $535)
```

### For Debit Spreads / Long Options
- **Long call (directional)**: Buy the 0.40–0.55 delta strike (near ATM for maximum sensitivity)
- **Short call (spread cap)**: Sell the 0.20–0.25 delta strike (1 SD above target)
- **Target move**: Long strike + (width of spread) = rough profit target

### For Straddles / Strangles
- **ATM straddle**: Buy the strike closest to current price for both call and put
- **OTM strangle**: Buy 0.25-delta call + 0.25-delta put
- **Breakeven**: Current price ± total premium paid

---

## Part 4: Position Sizing Calculator

```
Max Risk ($) = Account Size × Risk Per Trade (%)
             = $50,000 × 3% = $1,500 max risk this trade

For credit spreads:
  Max loss per spread = (Width of strikes − credit received) × 100
  Contracts = Max Risk ÷ Max Loss per Spread
  Example: 5-wide spread, $1.80 credit
    Max loss = ($5.00 − $1.80) × 100 = $320 per contract
    Contracts = $1,500 ÷ $320 = 4.7 → round down to 4 contracts

For long options:
  Max loss = premium paid × 100 per contract
  Contracts = Max Risk ÷ (Premium × 100)
  Example: Buying $3.50 call
    Max loss = $3.50 × 100 = $350 per contract
    Contracts = $1,500 ÷ $350 = 4.3 → round down to 4 contracts

For iron condors:
  Max loss = (Width of widest spread − net credit) × 100
  Contracts = Max Risk ÷ Max Loss per Iron Condor
```

**Rounding rule**: Always round DOWN to avoid exceeding your risk limit.
**Sector limit**: No more than 15% of account in one sector at a time.
**Portfolio limit**: No more than 8–10 simultaneous positions.

---

## Part 5: The Complete Trade Plan Template

Generate every trade plan in this exact format:

```
╔══════════════════════════════════════════════════════════════╗
║               OPTIONS TRADE PLAN                             ║
╚══════════════════════════════════════════════════════════════╝

TRADE OVERVIEW
  Underlying:       [Ticker] at $[price]
  Strategy:         [Strategy name]
  Market View:      [Bullish/Bearish/Neutral] — [brief thesis]
  Trade Type:       [Credit/Debit]
  Risk Profile:     [Defined risk / Undefined risk]

THE LEGS (Enter as a single order — all legs simultaneously)
  Leg 1:  [BUY/SELL] [QTY] [TICKER] [EXPIRY] [STRIKE] [CALL/PUT]  @ $[mid price]
  Leg 2:  [BUY/SELL] [QTY] [TICKER] [EXPIRY] [STRIKE] [CALL/PUT]  @ $[mid price]
  [Additional legs if applicable]

  Net Credit/Debit:     $[X.XX] per share / $[X×100] per contract
  Order Type:           Limit at $[mid] (use mid price, adjust by $0.05 if needed)

POSITION PARAMETERS
  Expiration:           [Date] ([DTE] DTE)
  IV Rank at Entry:     ~[IVR]
  Account Size:         $[account]
  Contracts:            [N] contracts
  Buying Power Used:    ~$[BP] ([X]% of account)
  Total Credit Collected: $[amount]   OR   Total Debit Paid: $[amount]

PROFIT & LOSS
  Max Profit:           $[amount] (if stock stays between [lower] and [upper] at expiry)
  Max Loss:             $[amount] (if stock moves beyond [range])
  Breakeven(s):         $[lower BE] and $[upper BE]
  Profit Zone:          Between $[X] and $[Y] at expiration

EXIT RULES — FOLLOW THESE WITHOUT EXCEPTION
  Profit Target:        Close when position value drops to $[50% of credit] (lock in 50% profit)
                        → Target date: approximately [date = entry + ~21 days at 45 DTE entry]
  Stop Loss:            Close if position value rises to $[2× credit] (2× the credit)
                        OR if [short strike] is breached by $[X]
  Time Stop:            Close ALL positions at 21 DTE regardless of P&L
                        → Hard close date: [expiry − 21 days]
  Early Close:          If 50% profit is hit before [date], close early and redeploy

ADJUSTMENT RULES
  If short put side tested (stock falls to $[short put strike ± $5]):
    → Option A: Close the entire position (take the loss, move on)
    → Option B: Roll the put spread down and out by 30 days for a net credit ≥ $0.50
    → Do NOT roll if you cannot collect at least $0.30 net credit
    → Do NOT roll more than once — if tested again after rolling, close.

  If short call side tested (stock rises to $[short call strike ± $5]):
    → Same rules apply on the call side

RISK SUMMARY
  Defined Risk?         [Yes/No]
  Max possible loss:    $[amount] ([X]% of account)
  Daily theta income:   +$[theta × contracts × 100]/day
  Vega exposure:        $[vega × contracts × 100] per 1% IV move
  Delta at entry:       ≈[delta] ([neutral/slight bullish/slight bearish])

TRADE THESIS
  [2–3 sentences: Why this trade, why now, what makes this setup favorable]
  Key assumption: [e.g., "SPY stays between $480 and $535 through April 18"]
  What breaks this trade: [e.g., "A surprise FOMC statement or gap move > $30"]

PRE-TRADE CHECKLIST
  □ IV Rank confirmed ≥ [target] before entry?
  □ No earnings or major events within [DTE] days?
  □ Options chain liquid (OI > 500, spread < 15% of mid)?
  □ Position size ≤ 5% of account?
  □ Portfolio delta within target range after this trade?
  □ Profit target and stop loss entered as GTC orders immediately after fill?
```

---

## Part 6: Plan Variations by Strategy

### Iron Condor Plan
Use template above. Note in adjustment rules: if one side is breached, you can close just the challenged spread (not the whole condor) if the other side is profitable.

### Covered Call Plan
Extra field: "Underlying shares owned: [N] shares at avg cost $[X]"
Note: Call away risk — if stock rallies above strike, shares called away at strike price.

### Cash-Secured Put Plan
Extra field: "Assignment readiness: Hold $[strike × 100 × contracts] in cash ready for assignment"
Note: If assigned, you own [N×100] shares at effective cost = strike − premium.

### LEAPS Plan
- Use 2-year expiration minimum
- Buy deep ITM (0.75–0.85 delta) to minimize extrinsic value
- Set a stop: Close if stock falls below key support (e.g., 200-day MA)
- Roll strategy: Roll the LEAPS 6 months out when < 6 months remain to maintain long-dated exposure

### Directional Spread Plan
Note the "maximum efficiency zone": The spread makes most of its profit when stock is between the two strikes at expiration. Profit potential is capped — don't be greedy if it hits 80%+ of max.

---

## Part 7: Pre-Trade Final Validation

Before finalizing any plan, run this mental checklist:

**Strategy-Market Fit (most important)**
- Is the IV regime right for this strategy? (High IV for selling, low IV for buying)
- Does the strategy match the directional view?
- Does the strategy match the timeframe?

**Risk Check**
- Is max loss within the 5% account rule?
- Is the sector exposure within the 15% limit?
- Is the portfolio delta going in the right direction after this trade?

**Execution Check**
- Is the options chain liquid enough? (Check OI and spread)
- Is the expiration correct? (Not accidentally weekly when you wanted monthly)
- Are all legs entered as a SINGLE multi-leg order? (Never leg into a spread one option at a time)

**Psychology Check**
- Is this a trade based on your screening criteria, or are you reacting to FOMO or a tip?
- Can you afford to lose the max loss without it affecting your trading?
- Do you have a clear exit plan entered as a GTC order immediately after the fill?

---

## Part 8: Post-Trade Plan (Day 1 Actions)

Immediately after getting filled:

1. **Enter profit target as GTC limit order** — if you collected $3.50, set a buy-to-close at $1.75 (50% target)
2. **Set price alert at stop level** — alert when premium exceeds $7.00 (2× the credit)
3. **Set calendar reminder for 21 DTE** — force yourself to review at the gamma risk boundary
4. **Log the trade** in your trade journal (use options-trade-journal skill)
5. **Check portfolio Greeks update** — confirm new aggregate delta/theta/vega is within targets
6. **No touching** — plans are made before entry. Once in a trade, only exit rules determine actions. Don't improvise.

---

## How to Build the Plan Step by Step

When Sam gives you a trade idea:

1. **Ask for any missing required inputs** (underlying, price, view, account size, IVR)
2. **Run the strategy selection engine** — justify your choice
3. **Calculate the strikes** using the 1-SD formula
4. **Calculate position size** to the nearest whole contract
5. **Fill in the complete template** with all fields
6. **Run the validation checklist** — flag any concerns
7. **Summarize in 2 sentences**: "The plan is to [strategy] on [ticker] for a $[credit] credit. The maximum risk is $[amount] and the profit target is $[target] at 50% of max."

Never deliver a vague plan. Every field must be filled in.
