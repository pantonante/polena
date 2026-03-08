"""Rebalancing engine - orchestrates the full portfolio rebalancing workflow."""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from robo_advisor.analytics.returns import ReturnsCalculator
from robo_advisor.analytics.risk_metrics import RiskMetrics
from robo_advisor.costs.transaction import (
    TradeCost,
    TradeOrder,
    TransactionCostModel,
)
from robo_advisor.data.fetcher import DataFetcher
from robo_advisor.models.constraints import AllocationConstraints
from robo_advisor.models.etf_universe import ETFUniverse
from robo_advisor.models.portfolio import Portfolio
from robo_advisor.optimization.base import BaseOptimizer, OptimizationResult
from robo_advisor.optimization.mean_variance import MeanVarianceOptimizer
from robo_advisor.optimization.min_cvar import MinCVaROptimizer
from robo_advisor.optimization.risk_parity import RiskParityOptimizer


@dataclass
class RebalancingResult:
    """Complete result of rebalancing analysis.

    Attributes:
        current_weights: Current portfolio weights.
        target_weights: Optimized target weights.
        trades: List of trades to execute.
        trade_costs: Breakdown of costs per trade.
        total_transaction_cost: Total cost of all trades.
        current_metrics: Risk metrics of current portfolio.
        projected_metrics: Expected risk metrics after rebalancing.
        current_expense_ratio: Weighted expense ratio of current portfolio.
        projected_expense_ratio: Weighted expense ratio after rebalancing.
        optimization_result: Full optimization result.
        drift: Maximum allocation drift from target.
        should_rebalance: Whether rebalancing is recommended.
        portfolio_value: Total portfolio value.
        residual_cash: Cash left unallocated due to rounding shares to integers.
    """

    current_weights: dict[str, float]
    target_weights: dict[str, float]
    trades: list[TradeOrder]
    trade_costs: list[TradeCost]
    total_transaction_cost: float
    current_metrics: dict[str, float]
    projected_metrics: dict[str, float]
    current_expense_ratio: float
    projected_expense_ratio: float
    optimization_result: OptimizationResult
    drift: float
    should_rebalance: bool
    portfolio_value: float
    residual_cash: float = 0.0
    current_allocation_by_class: dict[str, float] = field(default_factory=dict)
    target_allocation_by_class: dict[str, float] = field(default_factory=dict)


class RebalancingEngine:
    """Orchestrates the complete portfolio rebalancing workflow.

    Responsibilities:
    1. Load portfolio and ETF universe
    2. Fetch market data
    3. Run optimization
    4. Calculate required trades
    5. Estimate transaction costs
    6. Apply rebalancing threshold
    """

    def __init__(
        self,
        lookback_years: int = 3,
        risk_free_rate: float = 0.05,
        rebalance_threshold: float = 0.05,
        commission_per_trade: float = 0.0,
        spread_bps: float = 5.0,
        min_trade_value: float = 100.0,
        cvar_confidence: float = 0.95,
    ) -> None:
        """Initialize RebalancingEngine.

        Args:
            lookback_years: Years of historical data for analysis.
            risk_free_rate: Annual risk-free rate.
            rebalance_threshold: Minimum drift to trigger rebalancing.
            commission_per_trade: Fixed commission per trade.
            spread_bps: Bid-ask spread in basis points.
            min_trade_value: Minimum trade size.
            cvar_confidence: Confidence level for CVaR.
        """
        self.lookback_years = lookback_years
        self.risk_free_rate = risk_free_rate
        self.rebalance_threshold = rebalance_threshold
        self.cvar_confidence = cvar_confidence

        self.data_fetcher = DataFetcher(
            lookback_years=lookback_years,
            benchmark_ticker="SPY",
        )

        self.cost_model = TransactionCostModel(
            commission_per_trade=commission_per_trade,
            spread_bps=spread_bps,
            min_trade_value=min_trade_value,
        )

        self.risk_metrics = RiskMetrics(
            risk_free_rate=risk_free_rate,
            cvar_confidence=cvar_confidence,
        )

        self.returns_calc = ReturnsCalculator()

    def create_optimizer(
        self,
        method: str,
        **kwargs: Any,
    ) -> BaseOptimizer:
        """Create an optimizer based on method name.

        Args:
            method: Optimization method ('mean_variance', 'risk_parity', 'min_cvar').
            **kwargs: Additional parameters for the optimizer.

        Returns:
            Configured optimizer instance.
        """
        if method == "mean_variance":
            return MeanVarianceOptimizer(
                risk_free_rate=self.risk_free_rate,
                risk_aversion=kwargs.get("risk_aversion", 1.0),
                mode=kwargs.get("mode", "max_sharpe"),
            )
        elif method == "risk_parity":
            return RiskParityOptimizer(
                risk_free_rate=self.risk_free_rate,
                target_volatility=kwargs.get("target_volatility"),
            )
        elif method == "min_cvar":
            return MinCVaROptimizer(
                risk_free_rate=self.risk_free_rate,
                confidence_level=kwargs.get("confidence_level", self.cvar_confidence),
                min_expected_return=kwargs.get("min_expected_return", 0.0),
            )
        else:
            raise ValueError(f"Unknown optimization method: {method}")

    def calculate_drift(
        self,
        current_allocation: dict[str, float],
        target_allocation: dict[str, float],
    ) -> float:
        """Calculate maximum drift from target allocation.

        Args:
            current_allocation: Current allocation by asset class.
            target_allocation: Target allocation by asset class.

        Returns:
            Maximum absolute drift across asset classes.
        """
        max_drift = 0.0
        all_classes = set(current_allocation.keys()) | set(target_allocation.keys())

        for ac in all_classes:
            current = current_allocation.get(ac, 0.0)
            target = target_allocation.get(ac, 0.0)
            drift = abs(current - target)
            max_drift = max(max_drift, drift)

        return max_drift

    def run(
        self,
        portfolio: Portfolio,
        etf_universe: ETFUniverse,
        constraints: AllocationConstraints,
        optimizer_method: str = "mean_variance",
        optimizer_params: dict[str, Any] | None = None,
    ) -> RebalancingResult:
        """Run the complete rebalancing analysis.

        Args:
            portfolio: Current portfolio.
            etf_universe: Available ETFs.
            constraints: Allocation constraints.
            optimizer_method: Optimization method to use.
            optimizer_params: Additional parameters for optimizer.

        Returns:
            Complete RebalancingResult.
        """
        optimizer_params = optimizer_params or {}

        # Get all tickers (from portfolio and universe)
        portfolio_tickers = portfolio.get_tickers()
        universe_tickers = etf_universe.get_tickers()
        all_tickers = list(set(portfolio_tickers + universe_tickers))

        # Fetch ETF info (needed for asset class inference from yfinance categories)
        print("Fetching ETF metadata...")
        etf_universe.fetch_all_info()

        # Fetch current prices
        print("Fetching current prices...")
        current_prices = self.data_fetcher.get_current_prices(all_tickers)

        # Calculate portfolio value
        portfolio_value = portfolio.total_market_value(current_prices)

        # Get current weights
        current_weights = portfolio.get_weights(current_prices)

        # Get ticker to asset class mapping (must be after fetch_all_info for correct categories)
        ticker_to_ac = etf_universe.get_ticker_to_asset_class()

        # Current allocation by asset class
        current_allocation = portfolio.get_allocation_by_asset_class(
            current_prices, ticker_to_ac
        )

        # Set up volume data for cost model
        volumes = {e.ticker: e.avg_daily_volume for e in etf_universe.etfs}
        self.cost_model.set_volumes(volumes)

        # Fetch historical returns
        print("Fetching historical data...")
        returns = self.data_fetcher.get_returns(
            universe_tickers, include_benchmark=True
        )

        # Get benchmark returns
        benchmark_returns = (
            returns[self.data_fetcher.benchmark_ticker]
            if self.data_fetcher.benchmark_ticker in returns.columns
            else None
        )

        # Calculate current portfolio returns
        current_portfolio_returns = self.returns_calc.calculate_portfolio_returns(
            returns, current_weights
        )

        # Calculate current risk metrics
        current_metrics = self.risk_metrics.calculate_all(
            current_portfolio_returns, benchmark_returns
        )

        # Run optimization
        print(f"Running {optimizer_method} optimization...")
        optimizer = self.create_optimizer(optimizer_method, **optimizer_params)
        optimization_result = optimizer.optimize(
            returns[universe_tickers],
            constraints,
            ticker_to_ac,
        )

        if not optimization_result.success:
            print(f"Warning: {optimization_result.message}")

        target_weights = optimization_result.weights

        # Calculate target allocation by asset class
        target_allocation: dict[str, float] = {}
        for ticker, weight in target_weights.items():
            if weight > 0:
                ac = ticker_to_ac.get(ticker, "unknown")
                target_allocation[ac] = target_allocation.get(ac, 0.0) + weight

        # Calculate drift
        drift = self.calculate_drift(current_allocation, constraints.asset_class_targets)

        # Should we rebalance?
        should_rebalance = drift >= self.rebalance_threshold

        # Calculate projected portfolio returns
        projected_portfolio_returns = self.returns_calc.calculate_portfolio_returns(
            returns, target_weights
        )

        # Calculate projected risk metrics
        projected_metrics = self.risk_metrics.calculate_all(
            projected_portfolio_returns, benchmark_returns
        )

        # Calculate trades (shares rounded to integers)
        trades, residual_cash = self.cost_model.calculate_rebalancing_trades(
            current_weights,
            target_weights,
            portfolio_value,
            current_prices,
        )

        # Filter small trades
        trades = self.cost_model.filter_small_trades(trades)

        # Calculate costs
        trade_costs, total_cost = self.cost_model.calculate_total_costs(trades)

        # Calculate expense ratios
        expense_ratios = etf_universe.get_expense_ratios()
        current_expense_ratio = etf_universe.weighted_expense_ratio(current_weights)
        projected_expense_ratio = etf_universe.weighted_expense_ratio(target_weights)

        return RebalancingResult(
            current_weights=current_weights,
            target_weights=target_weights,
            trades=trades,
            trade_costs=trade_costs,
            total_transaction_cost=total_cost,
            current_metrics=current_metrics,
            projected_metrics=projected_metrics,
            current_expense_ratio=current_expense_ratio,
            projected_expense_ratio=projected_expense_ratio,
            optimization_result=optimization_result,
            drift=drift,
            should_rebalance=should_rebalance,
            portfolio_value=portfolio_value,
            residual_cash=residual_cash,
            current_allocation_by_class=current_allocation,
            target_allocation_by_class=target_allocation,
        )


