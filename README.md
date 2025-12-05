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

| Argument | Default | Description |
|----------|---------|-------------|
| `--output` | `text` | Output format: `text` or `json` |

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

### JSON Output

```bash
python main.py \
  --portfolio data/sample_portfolio.json \
  --etfs data/sample_etfs.json \
  --allocation "equity:0.8,bond:0.2" \
  --output json > report.json
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

## Technical Details

### Optimization Methods

1. **Mean-Variance (Markowitz)**
   - Maximizes Sharpe ratio or utility function E[R] - λ/2 * σ²
   - Uses historical mean returns and covariance matrix
   - Subject to asset class and position constraints

2. **Risk Parity**
   - Equalizes risk contribution across assets
   - Risk contribution = weight × marginal risk contribution
   - Optionally scaled to target volatility

3. **Minimum CVaR**
   - Minimizes expected shortfall (tail risk)
   - Uses Rockafellar-Uryasev formulation
   - Solved via convex optimization (cvxpy)

### Transaction Cost Model

- **Commission**: Fixed cost per trade
- **Spread**: Proportional to trade value (in basis points)
- **Market Impact**: Square-root model based on participation rate

## License

MIT

