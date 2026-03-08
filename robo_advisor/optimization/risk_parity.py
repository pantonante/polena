"""Risk Parity portfolio optimization."""

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from robo_advisor.models.constraints import AllocationConstraints
from robo_advisor.optimization.base import BaseOptimizer, OptimizationResult


class RiskParityOptimizer(BaseOptimizer):
    """Risk Parity portfolio optimizer.

    Allocates weights such that each asset contributes equally to
    portfolio risk (volatility).

    The marginal risk contribution of asset i is:
        MRC_i = (Σw)_i / σ_p

    The risk contribution is:
        RC_i = w_i * MRC_i

    Risk parity sets RC_i = RC_j for all i, j.

    Attributes:
        target_volatility: Optional target portfolio volatility for scaling.
    """

    def __init__(
        self,
        risk_free_rate: float = 0.05,
        trading_days_per_year: int = 252,
        target_volatility: float | None = None,
    ) -> None:
        """Initialize Risk Parity optimizer.

        Args:
            risk_free_rate: Annual risk-free rate.
            trading_days_per_year: Trading days for annualization.
            target_volatility: Optional target annualized volatility.
        """
        super().__init__(risk_free_rate, trading_days_per_year)
        self.target_volatility = target_volatility

    def _risk_contribution(
        self, weights: np.ndarray, cov_matrix: np.ndarray
    ) -> np.ndarray:
        """Calculate risk contribution of each asset.

        Args:
            weights: Portfolio weights.
            cov_matrix: Covariance matrix.

        Returns:
            Array of risk contributions (sum to portfolio volatility).
        """
        port_vol = np.sqrt(weights @ cov_matrix @ weights)
        if port_vol < 1e-10:
            return np.zeros_like(weights)

        # Marginal risk contribution
        mrc = cov_matrix @ weights / port_vol

        # Risk contribution
        rc = weights * mrc

        return rc

    def _risk_parity_objective(
        self, weights: np.ndarray, cov_matrix: np.ndarray
    ) -> float:
        """Objective function for risk parity.

        Minimizes the sum of squared differences between risk contributions.

        Args:
            weights: Portfolio weights.
            cov_matrix: Covariance matrix.

        Returns:
            Objective value (0 when perfect risk parity).
        """
        rc = self._risk_contribution(weights, cov_matrix)
        n = len(weights)

        # Target: equal risk contribution
        target_rc = rc.sum() / n

        # Sum of squared deviations from target
        return np.sum((rc - target_rc) ** 2)

    def optimize(
        self,
        returns: pd.DataFrame,
        constraints: AllocationConstraints,
        ticker_to_asset_class: dict[str, str],
    ) -> OptimizationResult:
        """Optimize portfolio using Risk Parity.

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

                scipy_constraints.append(
                    {
                        "type": "ineq",
                        "fun": lambda w, idx=i, lb=min_bound: (ac_matrix[idx] @ w)
                        - lb,
                    }
                )

                scipy_constraints.append(
                    {
                        "type": "ineq",
                        "fun": lambda w, idx=i, ub=max_bound: ub
                        - (ac_matrix[idx] @ w),
                    }
                )

        # Position bounds
        min_weight, max_weight = constraints.get_position_bounds()
        # For risk parity, we typically want positive weights
        bounds = [(max(min_weight, 0.001), max_weight) for _ in range(n_assets)]

        # Objective function
        def objective(w: np.ndarray) -> float:
            return self._risk_parity_objective(w, cov_matrix)

        # Run optimization
        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=scipy_constraints,
            options={"maxiter": 1000, "ftol": 1e-12},
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

        optimal_weights = result.x

        # Apply target volatility scaling if specified
        if self.target_volatility is not None:
            current_vol = np.sqrt(optimal_weights @ cov_matrix @ optimal_weights)
            if current_vol > 0:
                scale = self.target_volatility / current_vol
                # Note: This scaling would typically involve leverage
                # For now, we just report the unlevered weights
                # but calculate stats as if scaled

        # Clean up tiny weights
        optimal_weights[optimal_weights < 1e-6] = 0.0
        if optimal_weights.sum() > 0:
            optimal_weights = optimal_weights / optimal_weights.sum()

        # Calculate final portfolio statistics
        port_return, port_vol, sharpe = self._calculate_portfolio_stats(
            optimal_weights, exp_returns, cov_matrix
        )

        weights_dict = {t: float(w) for t, w in zip(tickers, optimal_weights)}

        # Calculate risk contributions for reporting
        rc = self._risk_contribution(optimal_weights, cov_matrix)
        rc_pct = rc / rc.sum() if rc.sum() > 0 else rc

        return OptimizationResult(
            weights=weights_dict,
            expected_return=port_return,
            expected_volatility=port_vol,
            sharpe_ratio=sharpe,
            success=True,
            message=f"Risk Parity optimization converged. "
            f"Risk contribution range: {rc_pct.min():.2%} - {rc_pct.max():.2%}",
        )



