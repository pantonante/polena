"""Risk metrics calculations for portfolio analysis."""

import numpy as np
import pandas as pd
from scipy import stats

from robo_advisor.analytics.returns import ReturnsCalculator


class RiskMetrics:
    """Calculate risk metrics for portfolios.

    Attributes:
        risk_free_rate: Annual risk-free rate.
        trading_days_per_year: Number of trading days for annualization.
        cvar_confidence: Confidence level for CVaR calculation.
    """

    def __init__(
        self,
        risk_free_rate: float = 0.05,
        trading_days_per_year: int = 252,
        cvar_confidence: float = 0.95,
    ) -> None:
        """Initialize RiskMetrics.

        Args:
            risk_free_rate: Annual risk-free rate.
            trading_days_per_year: Trading days for annualization.
            cvar_confidence: Confidence level for CVaR (e.g., 0.95).
        """
        self.risk_free_rate = risk_free_rate
        self.trading_days_per_year = trading_days_per_year
        self.cvar_confidence = cvar_confidence
        self._returns_calc = ReturnsCalculator(trading_days_per_year)

    def volatility(self, returns: pd.Series, annualize: bool = True) -> float:
        """Calculate volatility (standard deviation of returns).

        Args:
            returns: Series of returns.
            annualize: Whether to annualize the result.

        Returns:
            Volatility value.
        """
        vol = returns.std()
        if annualize:
            vol *= np.sqrt(self.trading_days_per_year)
        return float(vol)

    def sharpe_ratio(
        self,
        returns: pd.Series,
        risk_free_rate: float | None = None,
    ) -> float:
        """Calculate Sharpe ratio.

        Sharpe = (E[R] - Rf) / σ

        Args:
            returns: Series of returns.
            risk_free_rate: Annual risk-free rate (uses default if None).

        Returns:
            Annualized Sharpe ratio.
        """
        rf = risk_free_rate if risk_free_rate is not None else self.risk_free_rate

        ann_return = self._returns_calc.annualize_return(returns)
        ann_vol = self.volatility(returns, annualize=True)

        if ann_vol == 0:
            return 0.0

        return (ann_return - rf) / ann_vol

    def sortino_ratio(
        self,
        returns: pd.Series,
        target_return: float = 0.0,
        risk_free_rate: float | None = None,
    ) -> float:
        """Calculate Sortino ratio (uses downside deviation).

        Sortino = (E[R] - Rf) / σ_downside

        Args:
            returns: Series of returns.
            target_return: Target return for downside calculation.
            risk_free_rate: Annual risk-free rate.

        Returns:
            Annualized Sortino ratio.
        """
        rf = risk_free_rate if risk_free_rate is not None else self.risk_free_rate

        ann_return = self._returns_calc.annualize_return(returns)

        # Calculate downside deviation
        downside_returns = returns[returns < target_return]
        if len(downside_returns) == 0:
            return float("inf") if ann_return > rf else 0.0

        downside_std = downside_returns.std() * np.sqrt(self.trading_days_per_year)

        if downside_std == 0:
            return 0.0

        return (ann_return - rf) / downside_std

    def max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown.

        Args:
            returns: Series of returns.

        Returns:
            Maximum drawdown as a positive decimal (e.g., 0.20 for 20% drawdown).
        """
        cumulative = self._returns_calc.cumulative_returns(returns)
        running_max = cumulative.expanding().max()
        drawdowns = (cumulative - running_max) / running_max
        return float(-drawdowns.min())

    def calmar_ratio(self, returns: pd.Series) -> float:
        """Calculate Calmar ratio (return / max drawdown).

        Args:
            returns: Series of returns.

        Returns:
            Calmar ratio.
        """
        ann_return = self._returns_calc.annualize_return(returns)
        mdd = self.max_drawdown(returns)

        if mdd == 0:
            return float("inf") if ann_return > 0 else 0.0

        return ann_return / mdd

    def var(
        self,
        returns: pd.Series,
        confidence: float | None = None,
        method: str = "historical",
    ) -> float:
        """Calculate Value at Risk (VaR).

        Args:
            returns: Series of returns.
            confidence: Confidence level (e.g., 0.95 for 95% VaR).
            method: 'historical' or 'parametric'.

        Returns:
            VaR as positive decimal (potential loss at confidence level).
        """
        conf = confidence if confidence is not None else self.cvar_confidence

        if method == "historical":
            var = np.percentile(returns, (1 - conf) * 100)
        elif method == "parametric":
            # Assume normal distribution
            mean = returns.mean()
            std = returns.std()
            var = stats.norm.ppf(1 - conf, mean, std)
        else:
            raise ValueError(f"Unknown VaR method: {method}")

        return float(-var)

    def cvar(
        self,
        returns: pd.Series,
        confidence: float | None = None,
    ) -> float:
        """Calculate Conditional Value at Risk (CVaR / Expected Shortfall).

        CVaR is the expected loss given that the loss exceeds VaR.

        Args:
            returns: Series of returns.
            confidence: Confidence level (e.g., 0.95 for 95% CVaR).

        Returns:
            CVaR as positive decimal.
        """
        conf = confidence if confidence is not None else self.cvar_confidence

        var_threshold = np.percentile(returns, (1 - conf) * 100)
        tail_losses = returns[returns <= var_threshold]

        if len(tail_losses) == 0:
            return self.var(returns, confidence)

        return float(-tail_losses.mean())

    def beta(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> float:
        """Calculate beta relative to a benchmark.

        Args:
            returns: Series of portfolio returns.
            benchmark_returns: Series of benchmark returns.

        Returns:
            Beta coefficient.
        """
        # Align series
        aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
        if len(aligned) < 2:
            return 1.0

        cov = aligned.iloc[:, 0].cov(aligned.iloc[:, 1])
        var = aligned.iloc[:, 1].var()

        if var == 0:
            return 0.0

        return float(cov / var)

    def alpha(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series,
        risk_free_rate: float | None = None,
    ) -> float:
        """Calculate Jensen's alpha.

        Alpha = R_p - (R_f + β * (R_m - R_f))

        Args:
            returns: Series of portfolio returns.
            benchmark_returns: Series of benchmark returns.
            risk_free_rate: Annual risk-free rate.

        Returns:
            Annualized alpha.
        """
        rf = risk_free_rate if risk_free_rate is not None else self.risk_free_rate

        port_return = self._returns_calc.annualize_return(returns)
        bench_return = self._returns_calc.annualize_return(benchmark_returns)
        beta_val = self.beta(returns, benchmark_returns)

        return port_return - (rf + beta_val * (bench_return - rf))

    def information_ratio(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> float:
        """Calculate information ratio.

        IR = (R_p - R_b) / σ(R_p - R_b)

        Args:
            returns: Series of portfolio returns.
            benchmark_returns: Series of benchmark returns.

        Returns:
            Annualized information ratio.
        """
        # Align series
        aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
        if len(aligned) < 2:
            return 0.0

        excess = aligned.iloc[:, 0] - aligned.iloc[:, 1]
        tracking_error = excess.std() * np.sqrt(self.trading_days_per_year)

        if tracking_error == 0:
            return 0.0

        ann_excess = self._returns_calc.annualize_return(
            aligned.iloc[:, 0]
        ) - self._returns_calc.annualize_return(aligned.iloc[:, 1])

        return ann_excess / tracking_error

    def tracking_error(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> float:
        """Calculate tracking error (volatility of excess returns).

        Args:
            returns: Series of portfolio returns.
            benchmark_returns: Series of benchmark returns.

        Returns:
            Annualized tracking error.
        """
        aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
        if len(aligned) < 2:
            return 0.0

        excess = aligned.iloc[:, 0] - aligned.iloc[:, 1]
        return float(excess.std() * np.sqrt(self.trading_days_per_year))

    def calculate_all(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series | None = None,
    ) -> dict[str, float]:
        """Calculate all risk metrics.

        Args:
            returns: Series of portfolio returns.
            benchmark_returns: Optional benchmark returns for relative metrics.

        Returns:
            Dictionary with all calculated metrics.
        """
        metrics = {
            "annualized_return": self._returns_calc.annualize_return(returns),
            "annualized_volatility": self.volatility(returns),
            "sharpe_ratio": self.sharpe_ratio(returns),
            "sortino_ratio": self.sortino_ratio(returns),
            "max_drawdown": self.max_drawdown(returns),
            "calmar_ratio": self.calmar_ratio(returns),
            "var_95": self.var(returns, 0.95),
            "cvar_95": self.cvar(returns, 0.95),
            "var_99": self.var(returns, 0.99),
            "cvar_99": self.cvar(returns, 0.99),
        }

        if benchmark_returns is not None:
            metrics.update(
                {
                    "beta": self.beta(returns, benchmark_returns),
                    "alpha": self.alpha(returns, benchmark_returns),
                    "information_ratio": self.information_ratio(
                        returns, benchmark_returns
                    ),
                    "tracking_error": self.tracking_error(returns, benchmark_returns),
                }
            )

        return metrics



