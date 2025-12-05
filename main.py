#!/usr/bin/env python3
"""Polena - A robo-advisor for portfolio rebalancing.

This CLI tool helps you rebalance your ETF portfolio using various
optimization strategies including Mean-Variance, Risk Parity, and
Minimum CVaR (Conditional Value at Risk).
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console

from robo_advisor.engine import RebalancingEngine
from robo_advisor.models.constraints import AllocationConstraints
from robo_advisor.models.etf_universe import ETFUniverse
from robo_advisor.models.portfolio import Portfolio
from robo_advisor.report import ReportGenerator


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Robo-advisor for portfolio rebalancing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic rebalancing with Mean-Variance optimization
  python main.py --portfolio data/portfolio.json --etfs data/etfs.json \\
      --allocation "equity:0.8,bond:0.2"

  # Risk Parity optimization with target volatility
  python main.py --portfolio data/portfolio.json --etfs data/etfs.json \\
      --allocation "equity:0.6,bond:0.4" --optimizer risk_parity \\
      --target-volatility 0.12

  # Minimum CVaR optimization with return constraint
  python main.py --portfolio data/portfolio.json --etfs data/etfs.json \\
      --allocation "equity:0.7,bond:0.3" --optimizer min_cvar \\
      --cvar-confidence 0.95 --min-expected-return 0.06

  # Output as JSON
  python main.py --portfolio data/portfolio.json --etfs data/etfs.json \\
      --allocation "equity:0.8,bond:0.2" --output json
        """,
    )

    # Required arguments
    parser.add_argument(
        "--portfolio",
        type=str,
        required=True,
        help="Path to current portfolio JSON file",
    )
    parser.add_argument(
        "--etfs",
        type=str,
        required=True,
        help="Path to ETF universe JSON file",
    )
    parser.add_argument(
        "--allocation",
        type=str,
        required=True,
        help="Target asset class allocation (e.g., 'equity:0.8,bond:0.2')",
    )

    # Optimizer selection
    parser.add_argument(
        "--optimizer",
        type=str,
        choices=["mean_variance", "risk_parity", "min_cvar"],
        default="mean_variance",
        help="Optimization method (default: mean_variance)",
    )

    # General parameters
    parser.add_argument(
        "--risk-free-rate",
        type=float,
        default=0.05,
        help="Annual risk-free rate (default: 0.05)",
    )
    parser.add_argument(
        "--lookback-years",
        type=int,
        default=3,
        help="Years of historical data to use (default: 3)",
    )

    # Mean-Variance parameters
    parser.add_argument(
        "--risk-aversion",
        type=float,
        default=1.0,
        help="Risk aversion coefficient for Mean-Variance (default: 1.0)",
    )
    parser.add_argument(
        "--mvo-mode",
        type=str,
        choices=["max_sharpe", "risk_aversion"],
        default="max_sharpe",
        help="Mean-Variance mode (default: max_sharpe)",
    )

    # Risk Parity parameters
    parser.add_argument(
        "--target-volatility",
        type=float,
        default=None,
        help="Target annual volatility for Risk Parity (optional)",
    )

    # CVaR parameters
    parser.add_argument(
        "--cvar-confidence",
        type=float,
        default=0.95,
        help="CVaR confidence level (default: 0.95)",
    )
    parser.add_argument(
        "--min-expected-return",
        type=float,
        default=0.0,
        help="Minimum expected annual return constraint (default: 0.0)",
    )

    # Transaction cost parameters
    parser.add_argument(
        "--commission-per-trade",
        type=float,
        default=0.0,
        help="Fixed commission per trade in dollars (default: 0.0)",
    )
    parser.add_argument(
        "--spread-bps",
        type=float,
        default=5.0,
        help="Estimated bid-ask spread in basis points (default: 5.0)",
    )
    parser.add_argument(
        "--min-trade-value",
        type=float,
        default=100.0,
        help="Minimum trade size in dollars (default: 100.0)",
    )

    # Rebalancing threshold
    parser.add_argument(
        "--rebalance-threshold",
        type=float,
        default=0.05,
        help="Minimum drift to trigger rebalancing (default: 0.05)",
    )

    # Constraint parameters
    parser.add_argument(
        "--allocation-tolerance",
        type=float,
        default=0.05,
        help="Allowed deviation from target allocation (default: 0.05)",
    )
    parser.add_argument(
        "--min-position-weight",
        type=float,
        default=0.0,
        help="Minimum weight for any position (default: 0.0)",
    )
    parser.add_argument(
        "--max-position-weight",
        type=float,
        default=1.0,
        help="Maximum weight for any position (default: 1.0)",
    )

    # Output format
    parser.add_argument(
        "--output",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()
    console = Console()

    try:
        # Load portfolio
        portfolio_path = Path(args.portfolio)
        if not portfolio_path.exists():
            console.print(f"[red]Error: Portfolio file not found: {args.portfolio}[/red]")
            return 1
        portfolio = Portfolio.from_json(portfolio_path)

        # Load ETF universe
        etfs_path = Path(args.etfs)
        if not etfs_path.exists():
            console.print(f"[red]Error: ETF universe file not found: {args.etfs}[/red]")
            return 1
        etf_universe = ETFUniverse.from_json(etfs_path)

        # Parse allocation constraints
        constraints = AllocationConstraints.from_allocation_string(
            args.allocation,
            tolerance=args.allocation_tolerance,
            min_weight=args.min_position_weight,
            max_weight=args.max_position_weight,
        )

        # Create engine
        engine = RebalancingEngine(
            lookback_years=args.lookback_years,
            risk_free_rate=args.risk_free_rate,
            rebalance_threshold=args.rebalance_threshold,
            commission_per_trade=args.commission_per_trade,
            spread_bps=args.spread_bps,
            min_trade_value=args.min_trade_value,
            cvar_confidence=args.cvar_confidence,
        )

        # Build optimizer parameters
        optimizer_params = {}

        if args.optimizer == "mean_variance":
            optimizer_params["risk_aversion"] = args.risk_aversion
            optimizer_params["mode"] = args.mvo_mode
        elif args.optimizer == "risk_parity":
            optimizer_params["target_volatility"] = args.target_volatility
        elif args.optimizer == "min_cvar":
            optimizer_params["confidence_level"] = args.cvar_confidence
            optimizer_params["min_expected_return"] = args.min_expected_return

        # Run rebalancing
        console.print("[cyan]Starting portfolio analysis...[/cyan]")
        result = engine.run(
            portfolio=portfolio,
            etf_universe=etf_universe,
            constraints=constraints,
            optimizer_method=args.optimizer,
            optimizer_params=optimizer_params,
        )

        # Generate report
        report_generator = ReportGenerator(console=console)
        output = report_generator.generate(result, output_format=args.output)

        if output is not None:
            # JSON output
            print(output)

        return 0

    except ValueError as e:
        console.print(f"[red]Validation error: {e}[/red]")
        return 1
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if args.output != "json":
            import traceback
            console.print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
