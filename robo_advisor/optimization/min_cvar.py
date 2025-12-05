"""Minimum CVaR (Conditional Value at Risk) portfolio optimization."""

import numpy as np
import pandas as pd

from robo_advisor.models.constraints import AllocationConstraints
from robo_advisor.optimization.base import BaseOptimizer, OptimizationResult

try:
    import cvxpy as cp

    CVXPY_AVAILABLE = True
except ImportError:
    CVXPY_AVAILABLE = False


class MinCVaROptimizer(BaseOptimizer):
    """Minimum CVaR (Conditional Value at Risk) portfolio optimizer.

    Minimizes the expected loss in the worst (1-α)% of cases.
    CVaR is also known as Expected Shortfall (ES).

    Uses the Rockafellar-Uryasev formulation for CVaR optimization:
        CVaR_α = min_{ζ} { ζ + (1/(1-α)) * E[max(-r - ζ, 0)] }

    Attributes:
        confidence_level: Confidence level for CVaR (e.g., 0.95).
        min_expected_return: Minimum expected return constraint.
    """

    def __init__(
        self,
        risk_free_rate: float = 0.05,
        trading_days_per_year: int = 252,
        confidence_level: float = 0.95,
        min_expected_return: float = 0.0,
    ) -> None:
        """Initialize MinCVaR optimizer.

        Args:
            risk_free_rate: Annual risk-free rate.
            trading_days_per_year: Trading days for annualization.
            confidence_level: CVaR confidence level (e.g., 0.95 for 95% CVaR).
            min_expected_return: Minimum expected annual return constraint.
        """
        super().__init__(risk_free_rate, trading_days_per_year)
        self.confidence_level = confidence_level
        self.min_expected_return = min_expected_return

        if not CVXPY_AVAILABLE:
            raise ImportError(
                "cvxpy is required for MinCVaR optimization. "
                "Install it with: pip install cvxpy"
            )

    def optimize(
        self,
        returns: pd.DataFrame,
        constraints: AllocationConstraints,
        ticker_to_asset_class: dict[str, str],
    ) -> OptimizationResult:
        """Optimize portfolio to minimize CVaR.

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

        # Get return scenarios (each row is a scenario)
        filtered_returns = returns[tickers]
        return_matrix = filtered_returns.values  # T x n_assets
        n_scenarios = return_matrix.shape[0]

        # Annualized expected returns for constraint
        ann_exp_returns = self._annualize_returns(filtered_returns).values

        # Covariance for post-optimization statistics
        cov_matrix = self._annualize_covariance(filtered_returns).values

        # CVaR parameter
        alpha = self.confidence_level
        beta = 1.0 / (1.0 - alpha)

        # Decision variables
        w = cp.Variable(n_assets)  # Portfolio weights
        zeta = cp.Variable()  # VaR auxiliary variable
        u = cp.Variable(n_scenarios)  # Auxiliary for CVaR linearization

        # Portfolio returns for each scenario
        portfolio_returns = return_matrix @ w

        # Objective: minimize CVaR
        # CVaR = zeta + (1/(1-alpha)) * mean(max(-r - zeta, 0))
        cvar = zeta + (beta / n_scenarios) * cp.sum(u)

        objective = cp.Minimize(cvar)

        # Constraints
        cvxpy_constraints = []

        # CVaR linearization constraints: u >= -portfolio_return - zeta
        cvxpy_constraints.append(u >= -portfolio_returns - zeta)
        cvxpy_constraints.append(u >= 0)

        # Weights sum to 1
        cvxpy_constraints.append(cp.sum(w) == 1)

        # Position bounds
        min_weight, max_weight = constraints.get_position_bounds()
        cvxpy_constraints.append(w >= min_weight)
        cvxpy_constraints.append(w <= max_weight)

        # Minimum expected return constraint (annualized)
        if self.min_expected_return > 0:
            cvxpy_constraints.append(w @ ann_exp_returns >= self.min_expected_return)

        # Asset class constraints
        asset_classes = list(constraints.asset_class_targets.keys())
        if asset_classes:
            ac_matrix = self._build_asset_class_matrix(
                tickers, ticker_to_asset_class, asset_classes
            )

            for i, ac in enumerate(asset_classes):
                min_bound, max_bound = constraints.get_asset_class_bounds(ac)
                ac_weights = ac_matrix[i] @ w
                cvxpy_constraints.append(ac_weights >= min_bound)
                cvxpy_constraints.append(ac_weights <= max_bound)

        # Solve the problem
        problem = cp.Problem(objective, cvxpy_constraints)

        try:
            problem.solve(solver=cp.ECOS, verbose=False)
        except Exception:
            try:
                problem.solve(solver=cp.SCS, verbose=False)
            except Exception as e:
                return OptimizationResult(
                    weights={t: 1.0 / n_assets for t in tickers},
                    expected_return=0.0,
                    expected_volatility=0.0,
                    sharpe_ratio=0.0,
                    success=False,
                    message=f"CVaR optimization failed: {e}",
                )

        if problem.status not in ["optimal", "optimal_inaccurate"]:
            return OptimizationResult(
                weights={t: 1.0 / n_assets for t in tickers},
                expected_return=0.0,
                expected_volatility=0.0,
                sharpe_ratio=0.0,
                success=False,
                message=f"CVaR optimization failed with status: {problem.status}",
            )

        # Extract optimal weights
        optimal_weights = np.array(w.value).flatten()

        # Clean up tiny weights
        optimal_weights[optimal_weights < 1e-6] = 0.0
        if optimal_weights.sum() > 0:
            optimal_weights = optimal_weights / optimal_weights.sum()

        # Calculate final portfolio statistics
        port_return, port_vol, sharpe = self._calculate_portfolio_stats(
            optimal_weights, ann_exp_returns, cov_matrix
        )

        # Calculate CVaR of optimal portfolio
        optimal_cvar = float(cvar.value) if cvar.value is not None else 0.0

        weights_dict = {t: float(w) for t, w in zip(tickers, optimal_weights)}

        return OptimizationResult(
            weights=weights_dict,
            expected_return=port_return,
            expected_volatility=port_vol,
            sharpe_ratio=sharpe,
            success=True,
            message=f"MinCVaR optimization converged. "
            f"Daily CVaR({self.confidence_level:.0%}): {-optimal_cvar:.4%}",
        )

