"""Return calculations for portfolio analysis."""

import numpy as np
import pandas as pd


class ReturnsCalculator:
    """Calculate various return metrics for portfolios."""

    def __init__(self, trading_days_per_year: int = 252) -> None:
        """Initialize ReturnsCalculator.

        Args:
            trading_days_per_year: Number of trading days for annualization.
        """
        self.trading_days_per_year = trading_days_per_year

    def calculate_portfolio_returns(
        self,
        asset_returns: pd.DataFrame,
        weights: dict[str, float],
    ) -> pd.Series:
        """Calculate portfolio returns given asset returns and weights.

        Args:
            asset_returns: DataFrame with asset returns (dates x tickers).
            weights: Dictionary mapping ticker to portfolio weight.

        Returns:
            Series of portfolio returns.
        """
        # Filter to only assets in weights
        tickers = [t for t in weights.keys() if t in asset_returns.columns]
        weight_array = np.array([weights[t] for t in tickers])

        # Ensure weights sum to 1
        weight_array = weight_array / weight_array.sum()

        returns = asset_returns[tickers].values @ weight_array
        return pd.Series(returns, index=asset_returns.index, name="portfolio")

    def annualize_return(self, daily_returns: pd.Series) -> float:
        """Annualize daily returns using geometric mean.

        Args:
            daily_returns: Series of daily returns.

        Returns:
            Annualized return.
        """
        # Geometric mean
        total_return = (1 + daily_returns).prod()
        n_years = len(daily_returns) / self.trading_days_per_year
        if n_years <= 0:
            return 0.0
        return total_return ** (1 / n_years) - 1

    def annualize_volatility(self, daily_returns: pd.Series) -> float:
        """Annualize daily volatility.

        Args:
            daily_returns: Series of daily returns.

        Returns:
            Annualized volatility (standard deviation).
        """
        return daily_returns.std() * np.sqrt(self.trading_days_per_year)

    def cumulative_returns(self, returns: pd.Series) -> pd.Series:
        """Calculate cumulative returns.

        Args:
            returns: Series of period returns.

        Returns:
            Series of cumulative returns (1 = break even).
        """
        return (1 + returns).cumprod()

    def rolling_returns(
        self,
        returns: pd.Series,
        window: int = 21,
    ) -> pd.Series:
        """Calculate rolling annualized returns.

        Args:
            returns: Series of daily returns.
            window: Rolling window size in days.

        Returns:
            Series of rolling annualized returns.
        """
        # Annualized rolling mean
        return returns.rolling(window).mean() * self.trading_days_per_year

    def calculate_excess_returns(
        self,
        returns: pd.Series,
        risk_free_rate: float,
    ) -> pd.Series:
        """Calculate excess returns over risk-free rate.

        Args:
            returns: Series of returns.
            risk_free_rate: Annual risk-free rate.

        Returns:
            Series of excess returns.
        """
        daily_rf = (1 + risk_free_rate) ** (1 / self.trading_days_per_year) - 1
        return returns - daily_rf

    def calculate_downside_returns(
        self,
        returns: pd.Series,
        target_return: float = 0.0,
    ) -> pd.Series:
        """Calculate downside returns (returns below target).

        Args:
            returns: Series of returns.
            target_return: Target return threshold.

        Returns:
            Series with returns below target (0 otherwise).
        """
        return returns.where(returns < target_return, 0)



