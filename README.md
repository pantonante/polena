# Polena - Robo Advisor for Portfolio Rebalancing

A sophisticated robo-advisor CLI tool for rebalancing ETF and stock portfolios using modern portfolio optimization techniques.

## Features

- **Multiple Optimization Strategies**
  - Mean-Variance (Markowitz) optimization with max Sharpe ratio or risk aversion modes
  - Risk Parity for equal risk contribution across assets
  - Minimum CVaR (Conditional Value at Risk) for tail risk optimization

- **Comprehensive Risk Metrics**
  - Sharpe ratio, Sortino ratio, Calmar ratio
  - VaR and CVaR at configurable confidence levels
  - Maximum drawdown, beta, alpha, tracking error

- **Transaction Cost Modeling**
  - Fixed commissions per trade
  - Bid-ask spread estimation
  - Market impact modeling for large orders
  - Minimum trade size filtering

- **Best Practices**
  - ETF expense ratio consideration
  - Asset class allocation constraints
  - Rebalancing threshold to avoid over-trading
  - Position limits (min/max weights)

## Installation

```bash
# Clone the repository
cd polena

# Install dependencies using uv
uv sync
```

## Quick Start

```bash
# Basic rebalancing with 80% equity, 20% bonds
python main.py \
  --portfolio data/sample_portfolio.json \
  --etfs data/sample_etfs.json \
  --allocation "equity:0.8,bond:0.2"
```

## Usage

### Command Line Arguments

#### Required Arguments

| Argument | Description |
|----------|-------------|
| `--portfolio` | Path to current portfolio JSON file |
| `--etfs` | Path to ETF universe JSON file |
| `--allocation` | Target asset class allocation (e.g., `equity:0.8,bond:0.2`) |

#### Optimizer Selection

| Argument | Default | Description |
|----------|---------|-------------|
| `--optimizer` | `mean_variance` | Optimization method: `mean_variance`, `risk_parity`, or `min_cvar` |

#### Risk Parameters

| Argument | Default | Description |
|----------|---------|-------------|
| `--risk-free-rate` | 0.05 | Annual risk-free rate |
| `--lookback-years` | 3 | Years of historical data for analysis |
| `--cvar-confidence` | 0.95 | CVaR confidence level (e.g., 0.95 for 95%) |

#### Mean-Variance Parameters

| Argument | Default | Description |
|----------|---------|-------------|
| `--risk-aversion` | 1.0 | Risk aversion coefficient λ (higher = more conservative) |
| `--mvo-mode` | `max_sharpe` | Mode: `max_sharpe` or `risk_aversion` |

#### Risk Parity Parameters

| Argument | Default | Description |
|----------|---------|-------------|
| `--target-volatility` | None | Target annualized volatility |

#### CVaR Parameters

| Argument | Default | Description |
|----------|---------|-------------|
| `--min-expected-return` | 0.0 | Minimum expected annual return constraint |

#### Transaction Cost Parameters

| Argument | Default | Description |
|----------|---------|-------------|
| `--commission-per-trade` | 0.0 | Fixed commission per trade ($) |
| `--spread-bps` | 5.0 | Estimated bid-ask spread (basis points) |
| `--min-trade-value` | 100.0 | Minimum trade size ($) |

#### Constraint Parameters

| Argument | Default | Description |
|----------|---------|-------------|
| `--rebalance-threshold` | 0.05 | Minimum drift to trigger rebalancing |
| `--allocation-tolerance` | 0.05 | Allowed deviation from target allocation |
| `--min-position-weight` | 0.0 | Minimum weight for any position |
| `--max-position-weight` | 1.0 | Maximum weight for any position |

#### Output

Reports are always written to the `output/` folder (created if missing) as `report_MM_YYYY.json` and `report_MM_YYYY.md` (e.g. `output/report_01_2025.json`, `output/report_01_2025.md`).

| Argument | Default | Description |
|----------|---------|-------------|
| `--output` | `text` | Terminal output format: `text` or `json` |

## Examples

### Mean-Variance Optimization (Max Sharpe)

```bash
python main.py \
  --portfolio data/sample_portfolio.json \
  --etfs data/sample_etfs.json \
  --allocation "equity:0.7,bond:0.3" \
  --optimizer mean_variance \
  --mvo-mode max_sharpe \
  --lookback-years 5
```

### Mean-Variance with Risk Aversion

```bash
python main.py \
  --portfolio data/sample_portfolio.json \
  --etfs data/sample_etfs.json \
  --allocation "equity:0.6,bond:0.4" \
  --optimizer mean_variance \
  --mvo-mode risk_aversion \
  --risk-aversion 2.5
```

### Risk Parity

```bash
python main.py \
  --portfolio data/sample_portfolio.json \
  --etfs data/sample_etfs.json \
  --allocation "equity:0.6,bond:0.4" \
  --optimizer risk_parity \
  --target-volatility 0.12
```

### Minimum CVaR

```bash
python main.py \
  --portfolio data/sample_portfolio.json \
  --etfs data/sample_etfs.json \
  --allocation "equity:0.7,bond:0.3" \
  --optimizer min_cvar \
  --cvar-confidence 0.95 \
  --min-expected-return 0.06
```

### With Transaction Costs

```bash
python main.py \
  --portfolio data/sample_portfolio.json \
  --etfs data/sample_etfs.json \
  --allocation "equity:0.8,bond:0.2" \
  --commission-per-trade 4.95 \
  --spread-bps 10 \
  --min-trade-value 500
```

### JSON Output to Terminal

```bash
# Print JSON to terminal (report files are still written to output/)
python main.py \
  --portfolio data/sample_portfolio.json \
  --etfs data/sample_etfs.json \
  --allocation "equity:0.8,bond:0.2" \
  --output json
```

## Data Formats

### Portfolio JSON

```json
{
  "holdings": [
    {"ticker": "VTI", "shares": 100, "cost_basis_per_share": 200.0},
    {"ticker": "BND", "shares": 50, "cost_basis_per_share": 80.0}
  ],
  "cash": 5000.0
}
```

### ETF Universe JSON

```json
{
  "etfs": [
    {
      "ticker": "VTI",
      "name": "Vanguard Total Stock Market ETF",
      "asset_class": "equity",
      "expense_ratio": 0.0003,
      "avg_daily_volume": 5000000
    },
    {
      "ticker": "BND",
      "name": "Vanguard Total Bond Market ETF",
      "asset_class": "bond",
      "expense_ratio": 0.0003,
      "avg_daily_volume": 8000000
    }
  ]
}
```

### Asset Classes

The following asset classes are supported:
- `equity` - Stocks and equity ETFs
- `bond` - Fixed income ETFs
- `real_estate` - REIT ETFs
- `commodity` - Commodity ETFs

## Architecture

```
robo_advisor/
├── models/           # Data models (Portfolio, ETFUniverse, Constraints)
├── data/             # Data fetching (yfinance integration)
├── analytics/        # Risk metrics and return calculations
├── optimization/     # Portfolio optimizers
├── costs/            # Transaction cost modeling
├── engine.py         # Orchestration engine
└── report.py         # Report generation
```

## Optimization Strategy Guide

This section provides detailed guidance on each supported optimization strategy to help decision makers choose the right approach for their investment goals.

---

### 1. Mean-Variance (Markowitz) Optimization

#### Description

Mean-Variance Optimization (MVO) is the foundational modern portfolio theory approach developed by Harry Markowitz in 1952. It constructs portfolios by finding the optimal trade-off between expected return and risk (measured by volatility/standard deviation).

The optimizer supports two modes:
- **Max Sharpe Ratio**: Finds the portfolio with the highest risk-adjusted return (return per unit of risk)
- **Risk Aversion**: Maximizes a utility function `U = E[R] - (λ/2) × σ²` where λ controls how much you penalize risk

#### How It Works

1. Estimates expected returns from historical data
2. Calculates the covariance matrix to capture asset correlations
3. Finds weights that either maximize Sharpe ratio or maximize utility given your risk aversion

#### Pros

| Advantage | Explanation |
|-----------|-------------|
| **Theoretically sound** | Nobel Prize-winning framework with strong mathematical foundation |
| **Intuitive risk-return tradeoff** | Directly balances the two things investors care about most |
| **Customizable risk tolerance** | Risk aversion parameter allows precise control over aggressiveness |
| **Well-understood** | Decades of academic research and industry adoption |
| **Efficient frontier** | Guarantees you're on the efficient frontier (no free lunch left on the table) |

#### Cons

| Disadvantage | Explanation |
|--------------|-------------|
| **Sensitive to inputs** | Small changes in expected returns can cause large weight changes |
| **Estimation error** | Historical returns may not predict future returns well |
| **Concentrated portfolios** | Can produce extreme weights if unconstrained |
| **Ignores higher moments** | Only considers mean and variance, not skewness or tail risks |
| **Garbage in, garbage out** | Results are only as good as your return/covariance estimates |

#### When to Use

- **Best for**: Investors with clear return expectations and willingness to accept volatility as the primary risk measure
- **Investment horizon**: Medium to long-term (3+ years)
- **Market conditions**: Works best in normal market conditions with stable correlations
- **Investor profile**: Sophisticated investors who understand and accept estimation uncertainty

#### Key Parameters

| Parameter | Recommendation |
|-----------|---------------|
| `--mvo-mode max_sharpe` | Use when you want the best risk-adjusted returns and don't have a specific risk budget |
| `--mvo-mode risk_aversion` | Use when you have a specific risk tolerance to express |
| `--risk-aversion` | Low (0.5-1): Aggressive. Medium (1-3): Balanced. High (3-5+): Conservative |
| `--lookback-years` | 3-5 years typically; longer for stability, shorter for relevance |

#### Example Use Cases

- Retirement portfolios with target return objectives
- Institutional investors with defined risk budgets
- Tactical allocation adjustments based on market views

---

### 2. Risk Parity

#### Description

Risk Parity allocates portfolio weights so that each asset contributes equally to total portfolio risk. Rather than focusing on dollar amounts or target returns, it equalizes the risk contribution of each holding.

The risk contribution of asset i is: `RC_i = w_i × (Σw)_i / σ_portfolio`

Risk parity seeks: `RC_equity = RC_bonds = RC_commodities = ...`

#### How It Works

1. Calculates the covariance matrix of asset returns
2. For any weight allocation, computes each asset's marginal risk contribution
3. Finds weights where each asset contributes the same amount of risk to the portfolio
4. Optionally scales to a target volatility level

#### Pros

| Advantage | Explanation |
|-----------|-------------|
| **No return forecasting needed** | Only uses covariance estimates, avoiding the hardest estimation problem |
| **Diversification by risk** | Guarantees no single asset dominates portfolio risk |
| **Robust to estimation error** | Less sensitive to input changes than mean-variance |
| **Balanced drawdowns** | Losses tend to be more evenly distributed across assets |
| **Intuitive philosophy** | "Equal risk, not equal dollars" is easy to explain |
| **Strong historical performance** | Has delivered good risk-adjusted returns across market cycles |

#### Cons

| Disadvantage | Explanation |
|--------------|-------------|
| **Ignores expected returns** | May underweight assets with high expected returns |
| **Overweights low-vol assets** | Typically leads to heavy bond allocations |
| **May require leverage** | To achieve competitive returns, leverage is often needed |
| **Correlation assumptions** | Assumes correlations remain stable (they don't in crises) |
| **Not optimal in theory** | Doesn't target the efficient frontier explicitly |
| **Lower expected returns** | Often sacrifices return for balanced risk exposure |

#### When to Use

- **Best for**: Investors prioritizing diversification and drawdown control over return maximization
- **Investment horizon**: Long-term (5+ years), where compounding and avoiding large drawdowns matter
- **Market conditions**: Particularly valuable when you have low conviction in return forecasts
- **Investor profile**: Risk-conscious investors, endowments, and those who've experienced painful concentrated losses

#### Key Parameters

| Parameter | Recommendation |
|-----------|---------------|
| `--target-volatility` | Set to your risk budget (e.g., 0.10 for 10% annual vol). Leave unset for natural risk parity weights |
| `--lookback-years` | 3-5 years; covariance estimates are more stable than return estimates |

#### Example Use Cases

- "All-Weather" style portfolios designed to perform across economic regimes
- Foundation/endowment portfolios prioritizing preservation
- Investors scarred by 2008 or other crashes who want balanced exposure
- Base strategic allocation when you lack strong market views

---

### 3. Minimum CVaR (Conditional Value at Risk)

#### Description

Minimum CVaR optimization focuses on tail risk—the expected loss during the worst market scenarios. CVaR (also called Expected Shortfall) answers: "When things go badly, how bad do they get?"

At the 95% confidence level, CVaR measures the average loss in the worst 5% of outcomes.

Uses the Rockafellar-Uryasev formulation: `CVaR_α = min{ζ + (1/(1-α)) × E[max(-r - ζ, 0)]}`

#### How It Works

1. Uses historical return scenarios (each day is treated as a possible future outcome)
2. Identifies the worst (1-α)% of portfolio returns under different weight allocations
3. Minimizes the average loss in those worst-case scenarios
4. Optionally constrains for a minimum expected return

#### Pros

| Advantage | Explanation |
|-----------|-------------|
| **Focuses on tail risk** | Directly addresses what investors fear most—large losses |
| **Coherent risk measure** | Mathematically well-behaved (subadditive), unlike VaR |
| **Scenario-based** | Uses actual historical return distributions, not just summary statistics |
| **Captures fat tails** | Accounts for the non-normal returns seen in real markets |
| **Regulatory alignment** | CVaR/ES is becoming the standard in banking regulations (Basel III) |
| **Downside focus** | Penalizes downside without penalizing upside volatility |

#### Cons

| Disadvantage | Explanation |
|--------------|-------------|
| **Data hungry** | Needs many historical observations to estimate tail behavior |
| **Computationally intensive** | Requires convex optimization (more complex than quadratic) |
| **Backward-looking** | Future tail events may differ from historical ones |
| **May be overly conservative** | Can sacrifice significant upside to avoid rare events |
| **Confidence level choice** | Results sensitive to α (95% vs 99% can give different portfolios) |
| **Black swan problem** | Can't protect against events not in the historical sample |

#### When to Use

- **Best for**: Investors with hard constraints on losses (can't afford to lose more than X%)
- **Investment horizon**: Any horizon where avoiding catastrophic loss matters
- **Market conditions**: Especially valuable in volatile or uncertain regimes
- **Investor profile**: 
  - Retirees who can't recover from large losses
  - Institutions with liability constraints
  - Anyone who prioritizes "not losing" over "maximizing gains"

#### Key Parameters

| Parameter | Recommendation |
|-----------|---------------|
| `--cvar-confidence` | 0.95 (5% tail) is standard; 0.99 for extreme conservatism |
| `--min-expected-return` | Set a floor if you need minimum growth (e.g., 0.04 for 4% annual) |
| `--lookback-years` | 5+ years recommended to capture diverse market conditions including downturns |

#### Example Use Cases

- Retirement portfolios where sequence-of-returns risk is critical
- Liability-driven investing (pension funds, insurance)
- Capital preservation mandates with maximum drawdown constraints
- Portfolios during periods of elevated market stress

---

### Strategy Comparison Summary

| Criterion | Mean-Variance | Risk Parity | Min CVaR |
|-----------|--------------|-------------|----------|
| **Primary objective** | Max risk-adjusted return | Equal risk contribution | Minimize tail risk |
| **Return forecasts needed** | Yes | No | Optional |
| **Complexity** | Medium | Low | High |
| **Typical equity allocation** | Variable (can be high) | Lower (balanced) | Variable (often lower) |
| **Best in normal markets** | ★★★★★ | ★★★★☆ | ★★★☆☆ |
| **Best in crisis** | ★★☆☆☆ | ★★★★☆ | ★★★★★ |
| **Estimation sensitivity** | High | Low | Medium |
| **Computational cost** | Low | Low | Medium |
| **Industry adoption** | Very High | High | Growing |

### Decision Framework

**Choose Mean-Variance when:**
- You have conviction in your return forecasts
- You want to target the theoretically optimal portfolio
- You can tolerate estimation-driven weight swings
- You're comfortable with volatility as your risk measure

**Choose Risk Parity when:**
- You lack strong return forecasts
- You want stable, balanced exposure across asset classes
- Long-term compounding matters more than short-term performance
- You've been burned by concentrated bets before

**Choose Min CVaR when:**
- You have hard loss constraints ("can't lose more than 15%")
- Tail risk and black swans keep you up at night
- You're in or near retirement (sequence risk matters)
- You're willing to sacrifice some upside for downside protection

---

## Technical Details

### Transaction Cost Model

- **Commission**: Fixed cost per trade
- **Spread**: Proportional to trade value (in basis points)
- **Market Impact**: Square-root model based on participation rate

## License

MIT



