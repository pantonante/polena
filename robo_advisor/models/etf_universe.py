"""ETF Universe model containing available investment options."""

from dataclasses import dataclass, field
from typing import Any
import json
from pathlib import Path


@dataclass
class ETF:
    """Represents a single ETF with its metadata."""

    ticker: str
    name: str
    asset_class: str  # equity, bond, commodity, real_estate, etc.
    expense_ratio: float  # Annual expense ratio (e.g., 0.0003 for 0.03%)
    avg_daily_volume: int = 0  # Average daily trading volume

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


@dataclass
class ETFUniverse:
    """Collection of available ETFs for investment."""

    etfs: list[ETF] = field(default_factory=list)

    @classmethod
    def from_json(cls, path: str | Path) -> "ETFUniverse":
        """Load ETF universe from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)

        etfs = [
            ETF(
                ticker=e["ticker"],
                name=e["name"],
                asset_class=e["asset_class"],
                expense_ratio=e["expense_ratio"],
                avg_daily_volume=e.get("avg_daily_volume", 0),
            )
            for e in data.get("etfs", [])
        ]

        return cls(etfs=etfs)

    def to_dict(self) -> dict[str, Any]:
        """Convert universe to dictionary."""
        return {
            "etfs": [
                {
                    "ticker": e.ticker,
                    "name": e.name,
                    "asset_class": e.asset_class,
                    "expense_ratio": e.expense_ratio,
                    "avg_daily_volume": e.avg_daily_volume,
                }
                for e in self.etfs
            ]
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

