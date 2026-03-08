"""Mean-Variance (Markowitz) portfolio optimization."""

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from robo_advisor.models.constraints import AllocationConstraints
from robo_advisor.optimization.base import BaseOptimizer, OptimizationResult


class MeanVarianceOptimizer(BaseOptimizer):
    """Mean-Variance (Markowitz) portfolio optimizer.

    Supports two modes:
    1. Maximum Sharpe Ratio: Find portfolio with highest risk-adjusted return.
    2. Risk Aversion: Maximize utility = E[R] - 0.5 * λ * σ²

    Attributes:
        risk_aversion: Risk aversion coefficient λ for utility optimization.
        mode: 'max_sharpe' or 'risk_aversion'.
    """

    def __init__(
        self,
        risk_free_rate: float = 0.05,
        trading_days_per_year: int = 252,
        risk_aversion: float = 1.0,
        mode: str = "max_sharpe",
    ) -> None:
        """Initialize Mean-Variance optimizer.

        Args:
            risk_free_rate: Annual risk-free rate.
            trading_days_per_year: Trading days for annualization.
            risk_aversion: Risk aversion coefficient (higher = more conservative).
            mode: 'max_sharpe' or 'risk_aversion'.
        """
        super().__init__(risk_free_rate, trading_days_per_year)
        self.risk_aversion = risk_aversion
        self.mode = mode

    def optimize(
        self,
        returns: pd.DataFrame,
        constraints: AllocationConstraints,
        ticker_to_asset_class: dict[str, str],
    ) -> OptimizationResult:
        """Optimize portfolio using Mean-Variance optimization.

        Args:
            returns: DataFrame of asset returns (dates x tickers).
            constraints: Allocation constraints to satisfy.
            ticker_to_asset_class: Mapping of ticker to asset class.

        Returns:
            OptimizationResult with optimal weights.
        """
        tickers = [t for t in returns.columns if constraints.is_ticker_allowed(t)]
        n_assets = len(tickers)

        if n_assets == 0:
            return OptimizationResult(
                weights={},
                expected_return=0.0,
                expected_volatility=0.0,
                sharpe_ratio=0.0,
                success=False,
                message="No assets available for optimization",
            )

        # Calculate annualized statistics
        filtered_returns = returns[tickers]
        exp_returns = self._annualize_returns(filtered_returns).values
        cov_matrix = self._annualize_covariance(filtered_returns).values

        # Initial weights (equal weight)
        x0 = np.ones(n_assets) / n_assets

        # Build constraints
        scipy_constraints = []

        # Weights sum to 1
        scipy_constraints.append({"type": "eq", "fun": lambda w: np.sum(w) - 1.0})

        # Asset class constraints
        asset_classes = list(constraints.asset_class_targets.keys())
        if asset_classes:
            ac_matrix = self._build_asset_class_matrix(
                tickers, ticker_to_asset_class, asset_classes
            )

            for i, ac in enumerate(asset_classes):
                min_bound, max_bound = constraints.get_asset_class_bounds(ac)

                # Min constraint: sum of weights in asset class >= min_bound
                scipy_constraints.append(
                    {
                        "type": "ineq",
                        "fun": lambda w, idx=i, lb=min_bound: (ac_matrix[idx] @ w)
                        - lb,
                    }
                )

                # Max constraint: sum of weights in asset class <= max_bound
                scipy_constraints.append(
                    {
                        "type": "ineq",
                        "fun": lambda w, idx=i, ub=max_bound: ub
                        - (ac_matrix[idx] @ w),
                    }
                )

        # Position bounds
        min_weight, max_weight = constraints.get_position_bounds()
        bounds = [(min_weight, max_weight) for _ in range(n_assets)]

        # Objective function
        if self.mode == "max_sharpe":

            def objective(w: np.ndarray) -> float:
                port_return = w @ exp_returns
                port_vol = np.sqrt(w @ cov_matrix @ w)
                if port_vol < 1e-10:
                    return 0.0
                # Negative because we minimize
                return -(port_return - self.risk_free_rate) / port_vol

        else:  # risk_aversion mode

            def objective(w: np.ndarray) -> float:
                port_return = w @ exp_returns
                port_var = w @ cov_matrix @ w
                # Maximize utility, so negate for minimization
                utility = port_return - 0.5 * self.risk_aversion * port_var
                return -utility

        # Run optimization
        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=scipy_constraints,
            options={"maxiter": 1000, "ftol": 1e-9},
        )

        if not result.success:
            return OptimizationResult(
                weights={t: 1.0 / n_assets for t in tickers},
                expected_return=0.0,
                expected_volatility=0.0,
                sharpe_ratio=0.0,
                success=False,
                message=f"Optimization failed: {result.message}",
            )

        # Extract optimal weights
        optimal_weights = result.x

        # Clean up tiny weights (numerical noise)
        optimal_weights[optimal_weights < 1e-6] = 0.0
        optimal_weights = optimal_weights / optimal_weights.sum()

        # Calculate final portfolio statistics
        port_return, port_vol, sharpe = self._calculate_portfolio_stats(
            optimal_weights, exp_returns, cov_matrix
        )

        weights_dict = {t: float(w) for t, w in zip(tickers, optimal_weights)}

        return OptimizationResult(
            weights=weights_dict,
            expected_return=port_return,
            expected_volatility=port_vol,
            sharpe_ratio=sharpe,
            success=True,
            message=f"Mean-Variance optimization ({self.mode}) converged",
        )



