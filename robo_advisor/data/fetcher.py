"""Data fetcher for market data using yfinance and optionally mstarpy."""

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf

# Optional mstarpy import
try:
    from mstarpy import Funds as MstarFunds
    MSTARPY_AVAILABLE = True
except ImportError:
    MSTARPY_AVAILABLE = False


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
        self._mstar_cache: dict[str, MstarFunds] = {} if MSTARPY_AVAILABLE else {}

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
        """Get detailed info for a ticker from yfinance.

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

    def get_mstar_fund(self, name: str) -> "MstarFunds | None":
        """Get Morningstar fund object by name.

        Args:
            name: Fund name to search for.

        Returns:
            MstarFunds object or None if not available/found.
        """
        if not MSTARPY_AVAILABLE:
            return None

        if name in self._mstar_cache:
            return self._mstar_cache[name]

        try:
            fund = MstarFunds(term=name, pageSize=5)
            self._mstar_cache[name] = fund
            return fund
        except Exception:
            return None

    def get_etf_info(self, ticker: str) -> dict[str, Any]:
        """Get comprehensive ETF information from yfinance.

        Args:
            ticker: ETF ticker symbol.

        Returns:
            Dictionary with ETF information including:
            - name: Full name of the ETF
            - shortName: Short name
            - category: Morningstar category
            - fundFamily: Fund family/issuer
            - expenseRatio: Net expense ratio (as decimal, e.g., 0.0003 for 0.03%)
            - totalAssets: Assets under management
            - averageVolume: Average daily volume
            - yield: Dividend yield
            - ytdReturn: Year-to-date return
            - threeYearReturn: 3-year average annual return
            - fiveYearReturn: 5-year average annual return
            - beta: 3-year beta
        """
        info = self.get_ticker_info(ticker)

        # Extract and normalize ETF-specific fields
        net_expense = info.get("netExpenseRatio")
        expense_ratio = net_expense / 100.0 if net_expense is not None else None

        return {
            "ticker": ticker,
            "name": info.get("longName") or info.get("shortName"),
            "shortName": info.get("shortName"),
            "category": info.get("category"),
            "fundFamily": info.get("fundFamily"),
            "expenseRatio": expense_ratio,
            "totalAssets": info.get("totalAssets"),
            "averageVolume": info.get("averageVolume", 0),
            "yield": info.get("yield"),
            "ytdReturn": info.get("ytdReturn"),
            "threeYearReturn": info.get("threeYearAverageReturn"),
            "fiveYearReturn": info.get("fiveYearAverageReturn"),
            "beta": info.get("beta3Year"),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
            "fiftyDayAverage": info.get("fiftyDayAverage"),
            "twoHundredDayAverage": info.get("twoHundredDayAverage"),
            "regularMarketPrice": info.get("regularMarketPrice"),
            "previousClose": info.get("previousClose"),
        }

    def get_morningstar_data(self, fund_name: str) -> dict[str, Any] | None:
        """Get additional data from Morningstar via mstarpy.

        Args:
            fund_name: Fund name to search for.

        Returns:
            Dictionary with Morningstar data including ratings, risk metrics,
            sector allocation, and trailing returns. Returns None if mstarpy
            is not available or data fetch fails.
        """
        fund = self.get_mstar_fund(fund_name)
        if fund is None:
            return None

        result: dict[str, Any] = {
            "name": fund.name,
            "isin": fund.isin,
        }

        # Get risk/volatility data
        try:
            risk_data = fund.riskVolatility()
            fund_risk = risk_data.get("fundRiskVolatility", {})
            result["riskMetrics"] = {
                "1year": fund_risk.get("for1Year"),
                "3year": fund_risk.get("for3Year"),
                "5year": fund_risk.get("for5Year"),
                "10year": fund_risk.get("for10Year"),
            }
        except Exception:
            pass

        # Get trailing returns
        try:
            returns_data = fund.trailingReturn()
            result["morningstarRating"] = {
                "overall": returns_data.get("overallMorningstarRating"),
                "3year": returns_data.get("morningstarRatingFor3Year"),
                "5year": returns_data.get("morningstarRatingFor5Year"),
                "10year": returns_data.get("morningstarRatingFor10Year"),
            }
            # Returns are in format: ['1Day', '1Week', '1Month', '3Month', 'YearToDate', '1Year', '3Year', '5Year', '10Year', '15Year', 'SinceInception']
            nav_returns = returns_data.get("totalReturnNAV", [])
            if len(nav_returns) >= 9:
                result["trailingReturns"] = {
                    "1day": float(nav_returns[0]) if nav_returns[0] else None,
                    "1week": float(nav_returns[1]) if nav_returns[1] else None,
                    "1month": float(nav_returns[2]) if nav_returns[2] else None,
                    "3month": float(nav_returns[3]) if nav_returns[3] else None,
                    "ytd": float(nav_returns[4]) if nav_returns[4] else None,
                    "1year": float(nav_returns[5]) if nav_returns[5] else None,
                    "3year": float(nav_returns[6]) if nav_returns[6] else None,
                    "5year": float(nav_returns[7]) if nav_returns[7] else None,
                    "10year": float(nav_returns[8]) if nav_returns[8] else None,
                }
            result["categoryName"] = returns_data.get("categoryName")
            result["categoryRank"] = returns_data.get("returnRank")
        except Exception:
            pass

        # Get sector allocation
        try:
            sector_data = fund.sector()
            equity_sector = sector_data.get("EQUITY", {}).get("fundPortfolio", {})
            if equity_sector:
                result["sectorAllocation"] = {
                    "technology": equity_sector.get("technology"),
                    "healthcare": equity_sector.get("healthcare"),
                    "financialServices": equity_sector.get("financialServices"),
                    "consumerCyclical": equity_sector.get("consumerCyclical"),
                    "consumerDefensive": equity_sector.get("consumerDefensive"),
                    "industrials": equity_sector.get("industrials"),
                    "energy": equity_sector.get("energy"),
                    "utilities": equity_sector.get("utilities"),
                    "realEstate": equity_sector.get("realEstate"),
                    "basicMaterials": equity_sector.get("basicMaterials"),
                    "communicationServices": equity_sector.get("communicationServices"),
                }
        except Exception:
            pass

        return result

    def get_multiple_etf_info(self, tickers: list[str]) -> dict[str, dict[str, Any]]:
        """Get comprehensive ETF information for multiple tickers.

        Args:
            tickers: List of ETF ticker symbols.

        Returns:
            Dictionary mapping ticker to ETF info dictionary.
        """
        return {ticker: self.get_etf_info(ticker) for ticker in tickers}

    def get_expense_ratio(self, ticker: str) -> float | None:
        """Get expense ratio for an ETF.

        Args:
            ticker: ETF ticker symbol.

        Returns:
            Expense ratio as decimal (e.g., 0.0003 for 0.03%), or None if not available.
        """
        info = self.get_ticker_info(ticker)
        # yfinance reports netExpenseRatio as percentage (e.g., 0.03 for 0.03%)
        net_expense = info.get("netExpenseRatio")
        if net_expense is not None:
            return net_expense / 100.0
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

    def get_etf_holdings(self, ticker: str) -> pd.DataFrame | None:
        """Get top holdings for an ETF.

        Args:
            ticker: ETF ticker symbol.

        Returns:
            DataFrame with holdings information, or None if not available.
        """
        try:
            etf = yf.Ticker(ticker)
            funds_data = etf.get_funds_data()
            if funds_data is not None:
                return funds_data.top_holdings
        except Exception:
            pass
        return None

    def get_etf_sector_weightings(self, ticker: str) -> dict[str, float] | None:
        """Get sector weightings for an ETF.

        Args:
            ticker: ETF ticker symbol.

        Returns:
            Dictionary mapping sector to weight, or None if not available.
        """
        try:
            etf = yf.Ticker(ticker)
            funds_data = etf.get_funds_data()
            if funds_data is not None and hasattr(funds_data, "sector_weightings"):
                return funds_data.sector_weightings
        except Exception:
            pass
        return None

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

    def get_dividend_history(self, ticker: str) -> pd.DataFrame:
        """Get dividend history for a ticker.

        Args:
            ticker: Ticker symbol.

        Returns:
            DataFrame with dividend history.
        """
        try:
            stock = yf.Ticker(ticker)
            dividends = stock.dividends
            return dividends.to_frame(name="dividend") if not dividends.empty else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    def get_splits_history(self, ticker: str) -> pd.DataFrame:
        """Get stock split history for a ticker.

        Args:
            ticker: Ticker symbol.

        Returns:
            DataFrame with split history.
        """
        try:
            stock = yf.Ticker(ticker)
            splits = stock.splits
            return splits.to_frame(name="split") if not splits.empty else pd.DataFrame()
        except Exception:
            return pd.DataFrame()


def is_mstarpy_available() -> bool:
    """Check if mstarpy is available for Morningstar data."""
    return MSTARPY_AVAILABLE
