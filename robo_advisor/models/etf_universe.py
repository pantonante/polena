"""ETF Universe model containing available investment options."""

from dataclasses import dataclass, field
from typing import Any
import json
from pathlib import Path

import yfinance as yf

# Optional mstarpy import
try:
    from mstarpy import Funds as MstarFunds
    MSTARPY_AVAILABLE = True
except ImportError:
    MSTARPY_AVAILABLE = False


# Mapping of yfinance categories to our asset classes
CATEGORY_TO_ASSET_CLASS: dict[str, str] = {
    # Equity categories
    "Large Blend": "equity",
    "Large Value": "equity",
    "Large Growth": "equity",
    "Mid-Cap Blend": "equity",
    "Mid-Cap Value": "equity",
    "Mid-Cap Growth": "equity",
    "Small Blend": "equity",
    "Small Value": "equity",
    "Small Growth": "equity",
    "Foreign Large Blend": "equity",
    "Foreign Large Value": "equity",
    "Foreign Large Growth": "equity",
    "Foreign Small/Mid Blend": "equity",
    "Foreign Small/Mid Value": "equity",
    "Foreign Small/Mid Growth": "equity",
    "Diversified Emerging Mkts": "equity",
    "China Region": "equity",
    "India Equity": "equity",
    "Japan Stock": "equity",
    "Pacific/Asia ex-Japan Stk": "equity",
    "Europe Stock": "equity",
    "Latin America Stock": "equity",
    "World Large Stock": "equity",
    "World Stock": "equity",
    "Technology": "equity",
    "Health": "equity",
    "Financial": "equity",
    "Consumer Cyclical": "equity",
    "Consumer Defensive": "equity",
    "Energy Limited Partnership": "equity",
    "Natural Resources": "equity",
    "Utilities": "equity",
    "Industrials": "equity",
    "Communications": "equity",
    # Bond categories
    "Intermediate Core Bond": "bond",
    "Intermediate Core-Plus Bond": "bond",
    "Short-Term Bond": "bond",
    "Ultrashort Bond": "bond",
    "Long-Term Bond": "bond",
    "High Yield Bond": "bond",
    "Multisector Bond": "bond",
    "Corporate Bond": "bond",
    "Inflation-Protected Bond": "bond",
    "Short-Term Inflation-Protected Bond": "bond",
    "World Bond": "bond",
    "World Bond-USD Hedged": "bond",
    "Global Bond-USD Hedged": "bond",
    "Emerging Markets Bond": "bond",
    "Emerging-Markets Local-Currency Bond": "bond",
    "Bank Loan": "bond",
    "Preferred Stock": "bond",
    "Muni National Interm": "bond",
    "Muni National Short": "bond",
    "Muni National Long": "bond",
    "Muni Single State Interm": "bond",
    "Muni California Intermediate": "bond",
    "Muni California Long": "bond",
    "Muni New York Intermediate": "bond",
    "Muni New York Long": "bond",
    "Target-Date Retirement": "bond",
    # Real estate categories
    "Real Estate": "real_estate",
    "Global Real Estate": "real_estate",
    # Commodity categories
    "Commodities Broad Basket": "commodity",
    "Commodities Focused": "commodity",
    "Commodities Agriculture": "commodity",
    "Commodities Energy": "commodity",
    "Commodities Precious Metals": "commodity",
    "Commodities Industrial Metals": "commodity",
    # Alternative categories
    "Long-Short Equity": "alternative",
    "Market Neutral": "alternative",
    "Multialternative": "alternative",
    "Managed Futures": "alternative",
    "Systematic Trend": "alternative",
    "Event Driven": "alternative",
    "Options Trading": "alternative",
    "Volatility": "alternative",
    # Money market
    "Money Market-Taxable": "cash",
    "Prime Money Market": "cash",
    "Government Money Market": "cash",
}


def _infer_asset_class_from_category(category: str | None) -> str:
    """Infer asset class from yfinance category.

    Args:
        category: The yfinance category string.

    Returns:
        Inferred asset class, defaults to 'equity' if unknown.
    """
    if category is None:
        return "equity"

    # Direct lookup
    if category in CATEGORY_TO_ASSET_CLASS:
        return CATEGORY_TO_ASSET_CLASS[category]

    # Fuzzy matching based on keywords
    category_lower = category.lower()
    if "bond" in category_lower or "fixed" in category_lower:
        return "bond"
    if "real estate" in category_lower or "reit" in category_lower:
        return "real_estate"
    if "commodit" in category_lower or "gold" in category_lower or "metal" in category_lower:
        return "commodity"
    if "money market" in category_lower or "cash" in category_lower:
        return "cash"

    # Default to equity
    return "equity"


@dataclass
class ETF:
    """Represents a single ETF with its metadata.

    Most data is fetched from yfinance. Only ticker and optionally asset_class
    need to be provided; other fields are populated via fetch_info().
    """

    ticker: str
    asset_class: str = "equity"  # equity, bond, commodity, real_estate, etc.
    _name: str | None = field(default=None, repr=False)
    _expense_ratio: float | None = field(default=None, repr=False)
    _avg_daily_volume: int | None = field(default=None, repr=False)
    _category: str | None = field(default=None, repr=False)
    _total_assets: float | None = field(default=None, repr=False)
    _fund_family: str | None = field(default=None, repr=False)
    _yield: float | None = field(default=None, repr=False)
    _ytd_return: float | None = field(default=None, repr=False)
    _three_year_return: float | None = field(default=None, repr=False)
    _five_year_return: float | None = field(default=None, repr=False)
    _beta: float | None = field(default=None, repr=False)
    _info_fetched: bool = field(default=False, repr=False)
    # Morningstar data (optional, from mstarpy)
    _morningstar_rating: int | None = field(default=None, repr=False)
    _sharpe_ratio_3y: float | None = field(default=None, repr=False)
    _alpha_3y: float | None = field(default=None, repr=False)
    _standard_deviation_3y: float | None = field(default=None, repr=False)
    _sector_allocation: dict[str, float] | None = field(default=None, repr=False)
    _mstar_fetched: bool = field(default=False, repr=False)

    @property
    def name(self) -> str:
        """Get ETF name, fetching from yfinance if needed."""
        if self._name is None and not self._info_fetched:
            self.fetch_info()
        return self._name or self.ticker

    @property
    def expense_ratio(self) -> float:
        """Get expense ratio, fetching from yfinance if needed."""
        if self._expense_ratio is None and not self._info_fetched:
            self.fetch_info()
        return self._expense_ratio or 0.0

    @property
    def avg_daily_volume(self) -> int:
        """Get average daily volume, fetching from yfinance if needed."""
        if self._avg_daily_volume is None and not self._info_fetched:
            self.fetch_info()
        return self._avg_daily_volume or 0

    @property
    def category(self) -> str | None:
        """Get yfinance category."""
        if not self._info_fetched:
            self.fetch_info()
        return self._category

    @property
    def total_assets(self) -> float | None:
        """Get total assets under management."""
        if not self._info_fetched:
            self.fetch_info()
        return self._total_assets

    @property
    def fund_family(self) -> str | None:
        """Get fund family/issuer."""
        if not self._info_fetched:
            self.fetch_info()
        return self._fund_family

    @property
    def dividend_yield(self) -> float | None:
        """Get dividend yield."""
        if not self._info_fetched:
            self.fetch_info()
        return self._yield

    @property
    def ytd_return(self) -> float | None:
        """Get year-to-date return."""
        if not self._info_fetched:
            self.fetch_info()
        return self._ytd_return

    @property
    def three_year_return(self) -> float | None:
        """Get 3-year average annual return."""
        if not self._info_fetched:
            self.fetch_info()
        return self._three_year_return

    @property
    def five_year_return(self) -> float | None:
        """Get 5-year average annual return."""
        if not self._info_fetched:
            self.fetch_info()
        return self._five_year_return

    @property
    def beta(self) -> float | None:
        """Get 3-year beta."""
        if not self._info_fetched:
            self.fetch_info()
        return self._beta

    @property
    def morningstar_rating(self) -> int | None:
        """Get Morningstar rating (1-5 stars). Requires mstarpy."""
        if not self._mstar_fetched and MSTARPY_AVAILABLE:
            self.fetch_morningstar_data()
        return self._morningstar_rating

    @property
    def sharpe_ratio_3y(self) -> float | None:
        """Get 3-year Sharpe ratio. Requires mstarpy."""
        if not self._mstar_fetched and MSTARPY_AVAILABLE:
            self.fetch_morningstar_data()
        return self._sharpe_ratio_3y

    @property
    def alpha_3y(self) -> float | None:
        """Get 3-year alpha. Requires mstarpy."""
        if not self._mstar_fetched and MSTARPY_AVAILABLE:
            self.fetch_morningstar_data()
        return self._alpha_3y

    @property
    def standard_deviation_3y(self) -> float | None:
        """Get 3-year standard deviation. Requires mstarpy."""
        if not self._mstar_fetched and MSTARPY_AVAILABLE:
            self.fetch_morningstar_data()
        return self._standard_deviation_3y

    @property
    def sector_allocation(self) -> dict[str, float] | None:
        """Get sector allocation. Requires mstarpy."""
        if not self._mstar_fetched and MSTARPY_AVAILABLE:
            self.fetch_morningstar_data()
        return self._sector_allocation

    def fetch_info(self) -> None:
        """Fetch ETF information from yfinance."""
        if self._info_fetched:
            return

        try:
            ticker_obj = yf.Ticker(self.ticker)
            info = ticker_obj.info

            self._name = info.get("longName") or info.get("shortName")
            self._category = info.get("category")
            self._fund_family = info.get("fundFamily")
            self._total_assets = info.get("totalAssets")
            self._avg_daily_volume = info.get("averageVolume", 0)
            self._yield = info.get("yield")
            self._ytd_return = info.get("ytdReturn")
            self._three_year_return = info.get("threeYearAverageReturn")
            self._five_year_return = info.get("fiveYearAverageReturn")
            self._beta = info.get("beta3Year")

            # Expense ratio: yfinance reports as percentage (e.g., 0.03 for 0.03%)
            # Convert to decimal (0.0003 for 0.03%)
            net_expense = info.get("netExpenseRatio")
            if net_expense is not None:
                self._expense_ratio = net_expense / 100.0

            # Infer asset class from category if not set
            if self.asset_class == "equity" and self._category:
                inferred = _infer_asset_class_from_category(self._category)
                if inferred != "equity":
                    self.asset_class = inferred

        except Exception as e:
            print(f"Warning: Could not fetch info for {self.ticker}: {e}")

        self._info_fetched = True

    def fetch_morningstar_data(self) -> None:
        """Fetch additional data from Morningstar via mstarpy."""
        if self._mstar_fetched or not MSTARPY_AVAILABLE:
            return

        try:
            # Make sure we have the name first
            if self._name is None:
                self.fetch_info()

            # Search by full name for better matching
            search_term = self._name or self.ticker
            fund = MstarFunds(term=search_term, pageSize=5)

            # Get risk/volatility data
            try:
                risk_data = fund.riskVolatility()
                fund_risk = risk_data.get("fundRiskVolatility", {})
                for3year = fund_risk.get("for3Year", {})
                if for3year:
                    self._sharpe_ratio_3y = for3year.get("sharpeRatio")
                    self._alpha_3y = for3year.get("alpha")
                    self._standard_deviation_3y = for3year.get("standardDeviation")
            except Exception:
                pass

            # Get rating
            try:
                returns_data = fund.trailingReturn()
                self._morningstar_rating = returns_data.get("overallMorningstarRating")
            except Exception:
                pass

            # Get sector allocation
            try:
                sector_data = fund.sector()
                equity_sector = sector_data.get("EQUITY", {}).get("fundPortfolio", {})
                if equity_sector:
                    self._sector_allocation = {
                        k: v for k, v in equity_sector.items()
                        if k != "portfolioDate" and v is not None
                    }
            except Exception:
                pass

        except Exception as e:
            print(f"Warning: Could not fetch Morningstar data for {self.ticker}: {e}")

        self._mstar_fetched = True

    def annual_expense_cost(self, value: float) -> float:
        """Calculate annual expense cost for a given value.

        Args:
            value: The dollar value of holdings in this ETF.

        Returns:
            Annual expense in dollars.
        """
        return value * self.expense_ratio

    def is_liquid(self, min_volume: int = 100000) -> bool:
        """Check if ETF has sufficient liquidity.

        Args:
            min_volume: Minimum acceptable daily volume.

        Returns:
            True if average daily volume exceeds minimum.
        """
        return self.avg_daily_volume >= min_volume

    def to_dict(self, include_morningstar: bool = True) -> dict[str, Any]:
        """Convert ETF to dictionary with all available info.

        Args:
            include_morningstar: Whether to include Morningstar data (if available).

        Returns:
            Dictionary with ETF information.
        """
        result = {
            "ticker": self.ticker,
            "name": self.name,
            "asset_class": self.asset_class,
            "category": self.category,
            "expense_ratio": self.expense_ratio,
            "avg_daily_volume": self.avg_daily_volume,
            "total_assets": self.total_assets,
            "fund_family": self.fund_family,
            "dividend_yield": self.dividend_yield,
            "ytd_return": self.ytd_return,
            "three_year_return": self.three_year_return,
            "five_year_return": self.five_year_return,
            "beta": self.beta,
        }

        if include_morningstar and MSTARPY_AVAILABLE:
            result["morningstar_rating"] = self.morningstar_rating
            result["sharpe_ratio_3y"] = self.sharpe_ratio_3y
            result["alpha_3y"] = self.alpha_3y
            result["standard_deviation_3y"] = self.standard_deviation_3y
            result["sector_allocation"] = self.sector_allocation

        return result


@dataclass
class ETFUniverse:
    """Collection of available ETFs for investment."""

    etfs: list[ETF] = field(default_factory=list)
    _info_fetched: bool = field(default=False, repr=False)

    @classmethod
    def from_json(cls, path: str | Path) -> "ETFUniverse":
        """Load ETF universe from JSON file.

        The JSON file can be either:
        - A simple list of ticker strings: ["VTI", "BND", "VNQ"]
        - An object with "etfs" key containing ticker strings: {"etfs": ["VTI", "BND"]}

        Asset classes are automatically inferred from yfinance data.
        """
        with open(path, "r") as f:
            data = json.load(f)

        # Handle both formats: list of strings or dict with "etfs" key
        if isinstance(data, list):
            ticker_list = data
        else:
            ticker_list = data.get("etfs", [])

        etfs = [ETF(ticker=ticker) for ticker in ticker_list]

        return cls(etfs=etfs)

    @classmethod
    def from_tickers(cls, tickers: list[str]) -> "ETFUniverse":
        """Create ETF universe from a list of tickers.

        Asset classes will be inferred from yfinance data.
        """
        etfs = [ETF(ticker=ticker) for ticker in tickers]
        return cls(etfs=etfs)

    def fetch_all_info(self, include_morningstar: bool = False) -> None:
        """Fetch info for all ETFs from yfinance (and optionally Morningstar).

        Args:
            include_morningstar: Whether to also fetch Morningstar data.
        """
        if self._info_fetched:
            return

        for etf in self.etfs:
            etf.fetch_info()
            if include_morningstar and MSTARPY_AVAILABLE:
                etf.fetch_morningstar_data()

        self._info_fetched = True

    def to_dict(self, include_morningstar: bool = False) -> dict[str, Any]:
        """Convert universe to dictionary.

        Args:
            include_morningstar: Whether to include Morningstar data.

        Returns:
            Dictionary with ETF universe information.
        """
        return {
            "etfs": [e.to_dict(include_morningstar=include_morningstar) for e in self.etfs]
        }

    def get_etf(self, ticker: str) -> ETF | None:
        """Get ETF by ticker."""
        for e in self.etfs:
            if e.ticker == ticker:
                return e
        return None

    def get_tickers(self) -> list[str]:
        """Get list of all tickers."""
        return [e.ticker for e in self.etfs]

    def get_by_asset_class(self, asset_class: str) -> list[ETF]:
        """Get all ETFs of a specific asset class."""
        return [e for e in self.etfs if e.asset_class == asset_class]

    def get_asset_classes(self) -> set[str]:
        """Get set of all asset classes in the universe."""
        return {e.asset_class for e in self.etfs}

    def get_ticker_to_asset_class(self) -> dict[str, str]:
        """Get mapping of ticker to asset class."""
        return {e.ticker: e.asset_class for e in self.etfs}

    def get_expense_ratios(self) -> dict[str, float]:
        """Get mapping of ticker to expense ratio."""
        return {e.ticker: e.expense_ratio for e in self.etfs}

    def filter_liquid(self, min_volume: int = 100000) -> "ETFUniverse":
        """Return new universe containing only liquid ETFs.

        Args:
            min_volume: Minimum acceptable daily volume.

        Returns:
            New ETFUniverse with only liquid ETFs.
        """
        liquid_etfs = [e for e in self.etfs if e.is_liquid(min_volume)]
        return ETFUniverse(etfs=liquid_etfs)

    def weighted_expense_ratio(self, weights: dict[str, float]) -> float:
        """Calculate weighted average expense ratio.

        Args:
            weights: Dictionary mapping ticker to portfolio weight.

        Returns:
            Weighted average expense ratio.
        """
        total_expense = 0.0
        for ticker, weight in weights.items():
            etf = self.get_etf(ticker)
            if etf:
                total_expense += weight * etf.expense_ratio
        return total_expense

    def summary(self, include_morningstar: bool = False) -> str:
        """Get a summary of the ETF universe.

        Args:
            include_morningstar: Whether to include Morningstar ratings.

        Returns:
            Formatted summary string.
        """
        self.fetch_all_info(include_morningstar=include_morningstar)
        lines = [
            f"ETF Universe: {len(self.etfs)} ETFs",
            f"Asset classes: {', '.join(sorted(self.get_asset_classes()))}",
            "",
            "ETFs:",
        ]

        if include_morningstar and MSTARPY_AVAILABLE:
            for etf in self.etfs:
                expense_pct = etf.expense_ratio * 100
                rating = etf.morningstar_rating
                rating_str = f"{'★' * rating}{'☆' * (5 - rating)}" if rating else "N/A  "
                lines.append(
                    f"  {etf.ticker:6} - {etf.name[:35]:35} "
                    f"({etf.asset_class:12}) ER: {expense_pct:.2f}% | {rating_str}"
                )
        else:
            for etf in self.etfs:
                expense_pct = etf.expense_ratio * 100
                lines.append(
                    f"  {etf.ticker:6} - {etf.name[:40]:40} "
                    f"({etf.asset_class:12}) ER: {expense_pct:.2f}%"
                )

        return "\n".join(lines)


def is_mstarpy_available() -> bool:
    """Check if mstarpy is available for Morningstar data."""
    return MSTARPY_AVAILABLE
