"""Base optimizer class for portfolio optimization."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from robo_advisor.models.constraints import AllocationConstraints


@dataclass
class OptimizationResult:
    """Result of portfolio optimization.

    Attributes:
        weights: Dictionary mapping ticker to optimal weight.
        expected_return: Expected annual return of optimal portfolio.
        expected_volatility: Expected annual volatility of optimal portfolio.
        sharpe_ratio: Sharpe ratio of optimal portfolio.
        success: Whether optimization was successful.
        message: Additional information about the optimization.
    """

    weights: dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    success: bool = True
    message: str = ""


class BaseOptimizer(ABC):
    """Abstract base class for portfolio optimizers.

    All optimizers should inherit from this class and implement
    the optimize method.
    """

    def __init__(
        self,
        risk_free_rate: float = 0.05,
        trading_days_per_year: int = 252,
    ) -> None:
        """Initialize optimizer.

        Args:
            risk_free_rate: Annual risk-free rate.
            trading_days_per_year: Trading days for annualization.
        """
        self.risk_free_rate = risk_free_rate
        self.trading_days_per_year = trading_days_per_year

    @abstractmethod
    def optimize(
        self,
        returns: pd.DataFrame,
        constraints: AllocationConstraints,
        ticker_to_asset_class: dict[str, str],
    ) -> OptimizationResult:
        """Optimize portfolio weights.

        Args:
            returns: DataFrame of asset returns (dates x tickers).
            constraints: Allocation constraints to satisfy.
            ticker_to_asset_class: Mapping of ticker to asset class.

        Returns:
            OptimizationResult with optimal weights.
        """
        pass

    def _annualize_returns(self, returns: pd.DataFrame) -> pd.Series:
        """Annualize mean returns.

        Args:
            returns: DataFrame of daily returns.

        Returns:
            Series of annualized expected returns.
        """
        return returns.mean() * self.trading_days_per_year

    def _annualize_covariance(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Annualize covariance matrix.

        Args:
            returns: DataFrame of daily returns.

        Returns:
            Annualized covariance matrix.
        """
        return returns.cov() * self.trading_days_per_year

    def _calculate_portfolio_stats(
        self,
        weights: np.ndarray,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
    ) -> tuple[float, float, float]:
        """Calculate portfolio expected return, volatility, and Sharpe.

        Args:
            weights: Array of portfolio weights.
            expected_returns: Array of expected returns.
            cov_matrix: Covariance matrix.

        Returns:
            Tuple of (expected_return, volatility, sharpe_ratio).
        """
        port_return = float(weights @ expected_returns)
        port_vol = float(np.sqrt(weights @ cov_matrix @ weights))
        sharpe = (port_return - self.risk_free_rate) / port_vol if port_vol > 0 else 0.0
        return port_return, port_vol, sharpe

    def _build_asset_class_matrix(
        self,
        tickers: list[str],
        ticker_to_asset_class: dict[str, str],
        asset_classes: list[str],
    ) -> np.ndarray:
        """Build matrix mapping tickers to asset classes.

        Args:
            tickers: List of ticker symbols.
            ticker_to_asset_class: Mapping of ticker to asset class.
            asset_classes: List of asset classes.

        Returns:
            Matrix where A[i,j] = 1 if ticker j belongs to asset class i.
        """
        n_assets = len(tickers)
        n_classes = len(asset_classes)
        matrix = np.zeros((n_classes, n_assets))

        for j, ticker in enumerate(tickers):
            ac = ticker_to_asset_class.get(ticker, "unknown")
            if ac in asset_classes:
                i = asset_classes.index(ac)
                matrix[i, j] = 1.0

        return matrix



