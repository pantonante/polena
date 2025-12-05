"""Data fetcher for market data using yfinance."""

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf


class DataFetcher:
    """Fetches market data from Yahoo Finance.

    Attributes:
        lookback_years: Number of years of historical data to fetch.
        benchmark_ticker: Ticker for market benchmark (default: SPY).
    """

    def __init__(
        self,
        lookback_years: int = 3,
        benchmark_ticker: str = "SPY",
    ) -> None:
        """Initialize DataFetcher.

        Args:
            lookback_years: Years of historical data to fetch.
            benchmark_ticker: Ticker for market benchmark.
        """
        self.lookback_years = lookback_years
        self.benchmark_ticker = benchmark_ticker
        self._price_cache: dict[str, pd.DataFrame] = {}
        self._info_cache: dict[str, dict[str, Any]] = {}

    def get_historical_prices(
        self,
        tickers: list[str],
        include_benchmark: bool = True,
    ) -> pd.DataFrame:
        """Fetch historical adjusted close prices for given tickers.

        Args:
            tickers: List of ticker symbols.
            include_benchmark: Whether to include benchmark in data.

        Returns:
            DataFrame with dates as index and tickers as columns.
        """
        all_tickers = list(tickers)
        if include_benchmark and self.benchmark_ticker not in all_tickers:
            all_tickers.append(self.benchmark_ticker)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_years * 365)

        # Fetch data from yfinance
        data = yf.download(
            all_tickers,
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            progress=False,
            auto_adjust=True,
        )

        # Handle single ticker case
        if len(all_tickers) == 1:
            prices = data["Close"].to_frame(name=all_tickers[0])
        else:
            prices = data["Close"]

        # Drop rows with any missing values
        prices = prices.dropna()

        return prices

    def get_current_prices(self, tickers: list[str]) -> dict[str, float]:
        """Get current prices for given tickers.

        Args:
            tickers: List of ticker symbols.

        Returns:
            Dictionary mapping ticker to current price.
        """
        prices = {}
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                # Try to get the most recent price
                hist = stock.history(period="1d")
                if not hist.empty:
                    prices[ticker] = float(hist["Close"].iloc[-1])
                else:
                    # Fallback to info
                    info = stock.info
                    if "regularMarketPrice" in info:
                        prices[ticker] = float(info["regularMarketPrice"])
                    elif "previousClose" in info:
                        prices[ticker] = float(info["previousClose"])
            except Exception as e:
                print(f"Warning: Could not fetch price for {ticker}: {e}")
                prices[ticker] = 0.0

        return prices

    def get_returns(
        self,
        tickers: list[str],
        include_benchmark: bool = True,
    ) -> pd.DataFrame:
        """Calculate daily returns for given tickers.

        Args:
            tickers: List of ticker symbols.
            include_benchmark: Whether to include benchmark in data.

        Returns:
            DataFrame with daily returns.
        """
        prices = self.get_historical_prices(tickers, include_benchmark)
        returns = prices.pct_change().dropna()
        return returns

    def get_ticker_info(self, ticker: str) -> dict[str, Any]:
        """Get detailed info for a ticker.

        Args:
            ticker: Ticker symbol.

        Returns:
            Dictionary with ticker information.
        """
        if ticker in self._info_cache:
            return self._info_cache[ticker]

        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            self._info_cache[ticker] = info
            return info
        except Exception:
            return {}

    def get_expense_ratio(self, ticker: str) -> float | None:
        """Get expense ratio for an ETF.

        Args:
            ticker: ETF ticker symbol.

        Returns:
            Expense ratio as decimal, or None if not available.
        """
        info = self.get_ticker_info(ticker)
        # yfinance sometimes has this under different keys
        for key in ["expenseRatio", "annualReportExpenseRatio"]:
            if key in info and info[key] is not None:
                return float(info[key])
        return None

    def get_average_volume(self, ticker: str) -> int:
        """Get average daily trading volume for a ticker.

        Args:
            ticker: Ticker symbol.

        Returns:
            Average daily volume, or 0 if not available.
        """
        info = self.get_ticker_info(ticker)
        return int(info.get("averageVolume", 0))

    def calculate_covariance_matrix(
        self,
        tickers: list[str],
        annualize: bool = True,
    ) -> pd.DataFrame:
        """Calculate covariance matrix for given tickers.

        Args:
            tickers: List of ticker symbols.
            annualize: Whether to annualize the covariance.

        Returns:
            Covariance matrix as DataFrame.
        """
        returns = self.get_returns(tickers, include_benchmark=False)
        cov_matrix = returns.cov()

        if annualize:
            # Annualize assuming 252 trading days
            cov_matrix = cov_matrix * 252

        return cov_matrix

    def calculate_correlation_matrix(self, tickers: list[str]) -> pd.DataFrame:
        """Calculate correlation matrix for given tickers.

        Args:
            tickers: List of ticker symbols.

        Returns:
            Correlation matrix as DataFrame.
        """
        returns = self.get_returns(tickers, include_benchmark=False)
        return returns.corr()

    def get_expected_returns(
        self,
        tickers: list[str],
        method: str = "historical",
    ) -> pd.Series:
        """Estimate expected returns for given tickers.

        Args:
            tickers: List of ticker symbols.
            method: Method for estimation ('historical' or 'ewma').

        Returns:
            Series with annualized expected returns.
        """
        returns = self.get_returns(tickers, include_benchmark=False)

        if method == "historical":
            # Simple historical mean, annualized
            mean_returns = returns.mean() * 252
        elif method == "ewma":
            # Exponentially weighted moving average
            mean_returns = returns.ewm(span=60).mean().iloc[-1] * 252
        else:
            raise ValueError(f"Unknown method: {method}")

        return mean_returns

