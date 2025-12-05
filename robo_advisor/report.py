"""Report generation for rebalancing results."""

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from robo_advisor.engine import RebalancingResult


class ReportGenerator:
    """Generates comprehensive reports from rebalancing results.

    Supports both text (rich terminal) and JSON output formats.
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize ReportGenerator.

        Args:
            console: Rich console for output (creates new one if None).
        """
        self.console = console or Console()

    def generate(
        self,
        result: RebalancingResult,
        output_format: str = "text",
    ) -> str | None:
        """Generate report from rebalancing result.

        Args:
            result: RebalancingResult from RebalancingEngine.
            output_format: 'text' or 'json'.

        Returns:
            JSON string if format is 'json', None for 'text' (prints to console).
        """
        if output_format == "json":
            return self._generate_json(result)
        else:
            self._generate_text(result)
            return None

    def _generate_json(self, result: RebalancingResult) -> str:
        """Generate JSON report.

        Args:
            result: RebalancingResult from RebalancingEngine.

        Returns:
            JSON string.
        """
        output: dict[str, Any] = {
            "summary": {
                "portfolio_value": result.portfolio_value,
                "drift": result.drift,
                "should_rebalance": result.should_rebalance,
                "total_transaction_cost": result.total_transaction_cost,
                "current_expense_ratio": result.current_expense_ratio,
                "projected_expense_ratio": result.projected_expense_ratio,
            },
            "optimization": {
                "success": result.optimization_result.success,
                "message": result.optimization_result.message,
                "expected_return": result.optimization_result.expected_return,
                "expected_volatility": result.optimization_result.expected_volatility,
                "sharpe_ratio": result.optimization_result.sharpe_ratio,
            },
            "allocation": {
                "current_by_class": result.current_allocation_by_class,
                "target_by_class": result.target_allocation_by_class,
            },
            "weights": {
                "current": result.current_weights,
                "target": result.target_weights,
            },
            "trades": [
                {
                    "ticker": t.ticker,
                    "shares": t.shares,
                    "price": t.price,
                    "value": t.value,
                    "action": "BUY" if t.is_buy else "SELL",
                }
                for t in result.trades
            ],
            "costs": [
                {
                    "ticker": c.ticker,
                    "commission": c.commission,
                    "spread_cost": c.spread_cost,
                    "market_impact": c.market_impact,
                    "total": c.total,
                }
                for c in result.trade_costs
            ],
            "metrics": {
                "current": result.current_metrics,
                "projected": result.projected_metrics,
            },
        }

        return json.dumps(output, indent=2)

    def _generate_text(self, result: RebalancingResult) -> None:
        """Generate rich text report.

        Args:
            result: RebalancingResult from RebalancingEngine.
        """
        # Header
        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold cyan]Portfolio Rebalancing Report[/bold cyan]",
                border_style="cyan",
            )
        )
        self.console.print()

        # Summary Section
        self._print_summary(result)

        # Optimization Result
        self._print_optimization_result(result)

        # Asset Allocation
        self._print_allocation(result)

        # Portfolio Weights
        self._print_weights(result)

        # Recommended Trades
        self._print_trades(result)

        # Transaction Costs
        self._print_costs(result)

        # Risk Metrics Comparison
        self._print_metrics(result)

        # Recommendation
        self._print_recommendation(result)

    def _print_summary(self, result: RebalancingResult) -> None:
        """Print summary section."""
        table = Table(title="Summary", show_header=False, border_style="blue")
        table.add_column("Metric", style="dim")
        table.add_column("Value", style="bold")

        table.add_row("Portfolio Value", f"${result.portfolio_value:,.2f}")
        table.add_row("Current Drift", f"{result.drift:.2%}")
        table.add_row("Rebalance Threshold", f"{result.drift:.2%}")
        table.add_row(
            "Rebalancing Recommended",
            "[green]Yes[/green]" if result.should_rebalance else "[yellow]No[/yellow]",
        )
        table.add_row(
            "Total Transaction Cost", f"${result.total_transaction_cost:,.2f}"
        )
        table.add_row(
            "Cost as % of Portfolio",
            f"{result.total_transaction_cost / result.portfolio_value * 100:.4f}%"
            if result.portfolio_value > 0
            else "N/A",
        )

        self.console.print(table)
        self.console.print()

    def _print_optimization_result(self, result: RebalancingResult) -> None:
        """Print optimization result section."""
        opt = result.optimization_result

        status_style = "green" if opt.success else "red"
        status_text = "Success" if opt.success else "Failed"

        table = Table(title="Optimization Result", border_style="blue")
        table.add_column("Metric", style="dim")
        table.add_column("Value", style="bold")

        table.add_row("Status", f"[{status_style}]{status_text}[/{status_style}]")
        table.add_row("Message", opt.message)
        table.add_row("Expected Annual Return", f"{opt.expected_return:.2%}")
        table.add_row("Expected Volatility", f"{opt.expected_volatility:.2%}")
        table.add_row("Sharpe Ratio", f"{opt.sharpe_ratio:.3f}")

        self.console.print(table)
        self.console.print()

    def _print_allocation(self, result: RebalancingResult) -> None:
        """Print asset allocation comparison."""
        table = Table(title="Asset Allocation", border_style="blue")
        table.add_column("Asset Class", style="cyan")
        table.add_column("Current", justify="right")
        table.add_column("Target", justify="right")
        table.add_column("Difference", justify="right")

        all_classes = set(result.current_allocation_by_class.keys()) | set(
            result.target_allocation_by_class.keys()
        )

        for ac in sorted(all_classes):
            current = result.current_allocation_by_class.get(ac, 0.0)
            target = result.target_allocation_by_class.get(ac, 0.0)
            diff = target - current

            diff_style = "green" if diff >= 0 else "red"
            diff_text = f"[{diff_style}]{diff:+.2%}[/{diff_style}]"

            table.add_row(ac.title(), f"{current:.2%}", f"{target:.2%}", diff_text)

        self.console.print(table)
        self.console.print()

    def _print_weights(self, result: RebalancingResult) -> None:
        """Print portfolio weights."""
        table = Table(title="Portfolio Weights", border_style="blue")
        table.add_column("Ticker", style="cyan")
        table.add_column("Current", justify="right")
        table.add_column("Target", justify="right")
        table.add_column("Change", justify="right")

        all_tickers = set(result.current_weights.keys()) | set(
            result.target_weights.keys()
        )

        for ticker in sorted(all_tickers):
            if ticker == "_CASH":
                continue

            current = result.current_weights.get(ticker, 0.0)
            target = result.target_weights.get(ticker, 0.0)

            # Skip if both are zero
            if current < 0.001 and target < 0.001:
                continue

            diff = target - current
            diff_style = "green" if diff >= 0 else "red"
            diff_text = f"[{diff_style}]{diff:+.2%}[/{diff_style}]"

            table.add_row(ticker, f"{current:.2%}", f"{target:.2%}", diff_text)

        # Add cash row if present
        cash_current = result.current_weights.get("_CASH", 0.0)
        if cash_current > 0.001:
            table.add_row(
                "[dim]Cash[/dim]",
                f"{cash_current:.2%}",
                "0.00%",
                f"[red]{-cash_current:+.2%}[/red]",
            )

        self.console.print(table)
        self.console.print()

    def _print_trades(self, result: RebalancingResult) -> None:
        """Print recommended trades."""
        if not result.trades:
            self.console.print("[dim]No trades recommended.[/dim]")
            self.console.print()
            return

        table = Table(title="Recommended Trades", border_style="blue")
        table.add_column("Action", style="bold")
        table.add_column("Ticker", style="cyan")
        table.add_column("Shares", justify="right")
        table.add_column("Price", justify="right")
        table.add_column("Value", justify="right")

        # Sort: sells first, then buys
        sorted_trades = sorted(result.trades, key=lambda t: (t.is_buy, t.ticker))

        for trade in sorted_trades:
            action = "[green]BUY[/green]" if trade.is_buy else "[red]SELL[/red]"
            shares_text = f"{abs(trade.shares):,.2f}"

            table.add_row(
                action,
                trade.ticker,
                shares_text,
                f"${trade.price:,.2f}",
                f"${trade.value:,.2f}",
            )

        self.console.print(table)
        self.console.print()

    def _print_costs(self, result: RebalancingResult) -> None:
        """Print transaction costs breakdown."""
        if not result.trade_costs:
            return

        table = Table(title="Transaction Costs", border_style="blue")
        table.add_column("Ticker", style="cyan")
        table.add_column("Commission", justify="right")
        table.add_column("Spread", justify="right")
        table.add_column("Impact", justify="right")
        table.add_column("Total", justify="right", style="bold")

        total_commission = 0.0
        total_spread = 0.0
        total_impact = 0.0

        for cost in result.trade_costs:
            table.add_row(
                cost.ticker,
                f"${cost.commission:,.2f}",
                f"${cost.spread_cost:,.2f}",
                f"${cost.market_impact:,.2f}",
                f"${cost.total:,.2f}",
            )
            total_commission += cost.commission
            total_spread += cost.spread_cost
            total_impact += cost.market_impact

        # Add totals row
        table.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold]${total_commission:,.2f}[/bold]",
            f"[bold]${total_spread:,.2f}[/bold]",
            f"[bold]${total_impact:,.2f}[/bold]",
            f"[bold]${result.total_transaction_cost:,.2f}[/bold]",
        )

        self.console.print(table)
        self.console.print()

        # Expense ratio comparison
        expense_table = Table(title="Expense Ratios", border_style="blue")
        expense_table.add_column("Portfolio", style="dim")
        expense_table.add_column("Expense Ratio", justify="right")
        expense_table.add_column("Annual Cost", justify="right")

        current_annual = result.portfolio_value * result.current_expense_ratio
        projected_annual = result.portfolio_value * result.projected_expense_ratio

        expense_table.add_row(
            "Current",
            f"{result.current_expense_ratio:.4%}",
            f"${current_annual:,.2f}",
        )
        expense_table.add_row(
            "Projected",
            f"{result.projected_expense_ratio:.4%}",
            f"${projected_annual:,.2f}",
        )

        savings = current_annual - projected_annual
        if savings > 0:
            expense_table.add_row(
                "[green]Annual Savings[/green]",
                "",
                f"[green]${savings:,.2f}[/green]",
            )

        self.console.print(expense_table)
        self.console.print()

    def _print_metrics(self, result: RebalancingResult) -> None:
        """Print risk metrics comparison."""
        table = Table(title="Risk Metrics Comparison", border_style="blue")
        table.add_column("Metric", style="dim")
        table.add_column("Current", justify="right")
        table.add_column("Projected", justify="right")
        table.add_column("Change", justify="right")

        metrics_display = [
            ("annualized_return", "Annual Return", True),
            ("annualized_volatility", "Volatility", False),
            ("sharpe_ratio", "Sharpe Ratio", True),
            ("sortino_ratio", "Sortino Ratio", True),
            ("max_drawdown", "Max Drawdown", False),
            ("cvar_95", "CVaR (95%)", False),
            ("beta", "Beta", None),
            ("alpha", "Alpha", True),
        ]

        for key, label, higher_is_better in metrics_display:
            current_val = result.current_metrics.get(key)
            projected_val = result.projected_metrics.get(key)

            if current_val is None or projected_val is None:
                continue

            diff = projected_val - current_val

            # Determine if improvement
            if higher_is_better is None:
                diff_style = "dim"
            elif higher_is_better:
                diff_style = "green" if diff > 0 else "red"
            else:
                diff_style = "green" if diff < 0 else "red"

            # Format values
            if "ratio" in key.lower() or key in ("beta", "alpha"):
                current_str = f"{current_val:.3f}"
                projected_str = f"{projected_val:.3f}"
                diff_str = f"{diff:+.3f}"
            else:
                current_str = f"{current_val:.2%}"
                projected_str = f"{projected_val:.2%}"
                diff_str = f"{diff:+.2%}"

            table.add_row(
                label,
                current_str,
                projected_str,
                f"[{diff_style}]{diff_str}[/{diff_style}]",
            )

        self.console.print(table)
        self.console.print()

    def _print_recommendation(self, result: RebalancingResult) -> None:
        """Print final recommendation."""
        if result.should_rebalance:
            improvement = (
                result.projected_metrics.get("sharpe_ratio", 0)
                - result.current_metrics.get("sharpe_ratio", 0)
            )

            message = Text()
            message.append("Recommendation: ", style="bold")
            message.append("REBALANCE\n\n", style="bold green")
            message.append(f"Your portfolio has drifted {result.drift:.1%} from target.\n")
            message.append(
                f"Transaction cost: ${result.total_transaction_cost:.2f} "
                f"({result.total_transaction_cost / result.portfolio_value * 100:.3f}% of portfolio)\n"
            )
            message.append(f"Expected Sharpe improvement: {improvement:+.3f}")

            self.console.print(Panel(message, border_style="green"))
        else:
            message = Text()
            message.append("Recommendation: ", style="bold")
            message.append("HOLD\n\n", style="bold yellow")
            message.append(
                f"Current drift ({result.drift:.1%}) is within tolerance.\n"
            )
            message.append("No rebalancing needed at this time.")

            self.console.print(Panel(message, border_style="yellow"))

        self.console.print()

