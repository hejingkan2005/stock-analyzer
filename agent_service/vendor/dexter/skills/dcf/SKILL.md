---
name: dcf-valuation
description: Performs discounted cash flow (DCF) valuation analysis to estimate intrinsic value per share. Triggers when user asks for fair value, intrinsic value, DCF, valuation, "what is X worth", price target, undervalued/overvalued analysis, or wants to compare current price to fundamental value.
---

# DCF Valuation Skill

## Workflow Checklist

Copy and track progress:

```
DCF Analysis Progress:
- [ ] Step 1: Gather financial data
- [ ] Step 2: Calculate FCF growth rate
- [ ] Step 3: Estimate discount rate (WACC)
- [ ] Step 4: Project future cash flows (Years 1-5 + Terminal)
- [ ] Step 5: Calculate present value and fair value per share
- [ ] Step 6: Run sensitivity analysis
- [ ] Step 7: Validate results
- [ ] Step 8: Present results with caveats
```

## Step 1: Gather Financial Data

Call the appropriate finance tools with these queries:

### 1.1 Cash Flow History
Call `get_cash_flow_statements` with `period="annual"`, `limit=5`.

**Extract:** `free_cash_flow`, `net_cash_flow_from_operations`, `capital_expenditure`

**Fallback:** If `free_cash_flow` missing, calculate: `net_cash_flow_from_operations - capital_expenditure`

### 1.2 Financial Metrics
Call `get_financial_metrics_snapshot` for the ticker.

**Extract:** `market_cap`, `enterprise_value`, `free_cash_flow_growth`, `revenue_growth`, `return_on_invested_capital`, `debt_to_equity`, `free_cash_flow_per_share`

### 1.3 Balance Sheet
Call `get_balance_sheets` with `period="annual"`, `limit=1`.

**Extract:** `total_debt`, `cash_and_equivalents`, `current_investments`, `outstanding_shares`

**Fallback:** If `current_investments` missing, use 0

### 1.4 Analyst Estimates
Call `get_analyst_estimates`.

**Extract:** `earnings_per_share` (forward estimates by fiscal year)

**Use:** Calculate implied EPS growth rate for cross-validation

### 1.5 Current Price
Call `get_stock_price`.

### 1.6 Sector
Use the `sector` field returned by financial-metrics or screener data to choose a base WACC range from `sector-wacc.md`.

## Step 2: Calculate FCF Growth Rate

Calculate 5-year FCF CAGR from cash flow history.

**Cross-validate with:** `free_cash_flow_growth` (YoY), `revenue_growth`, analyst EPS growth

**Growth rate selection:**
- Stable FCF history → Use CAGR with 10-20% haircut
- Volatile FCF → Weight analyst estimates more heavily
- **Cap at 15%** (sustained higher growth is rare)

## Step 3: Estimate Discount Rate (WACC)

Use the `sector` to pick a base range from `sector-wacc.md`.

**Default assumptions:**
- Risk-free rate: 4%
- Equity risk premium: 5-6%
- Cost of debt: 5-6% pre-tax (~4% after-tax at 30% tax rate)

Calculate WACC using `debt_to_equity` for capital structure weights.

**Reasonableness check:** WACC should be 2-4% below `return_on_invested_capital` for value-creating companies.

## Step 4: Project Future Cash Flows

**Years 1-5:** Apply growth rate with 5% annual decay (multiply growth rate by 0.95, 0.90, 0.85, 0.80 for years 2-5).

**Terminal value:** Gordon Growth Model with 2.5% terminal growth.

## Step 5: Present Value & Fair Value

Discount all FCFs → sum to Enterprise Value → subtract Net Debt → divide by `outstanding_shares`.

## Step 6: Sensitivity Analysis

3×3 matrix: WACC (base ±1%) vs terminal growth (2.0%, 2.5%, 3.0%).

## Step 7: Validate

1. Calculated EV within 30% of reported `enterprise_value`.
2. Terminal value 50-80% of total EV for mature companies.
3. Per-share cross-check vs `free_cash_flow_per_share × 15-25`.

## Step 8: Output

Present:
1. Valuation summary (price vs fair value, upside/downside %)
2. Key inputs table with sources
3. 5-year projected FCF table
4. Sensitivity matrix
5. Caveats (DCF limitations + company-specific risks)
