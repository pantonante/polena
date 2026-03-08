"""Portfolio model representing current holdings."""

from dataclasses import dataclass, field
from typing import Any
import json
from pathlib import Path


@dataclass
class Holding:
    """A single holding in the portfolio."""

    ticker: str
    shares: float
    cost_basis_per_share: float

    @property
    def cost_basis_total(self) -> float:
        """Total cost basis for this holding."""
        return self.shares * self.cost_basis_per_share

    def market_value(self, current_price: float) -> float:
        """Calculate current market value."""
        return self.shares * current_price

    def unrealized_gain(self, current_price: float) -> float:
        """Calculate unrealized gain/loss."""
        return self.market_value(current_price) - self.cost_basis_total

    def unrealized_gain_pct(self, current_price: float) -> float:
        """Calculate unrealized gain/loss as percentage."""
        if self.cost_basis_total == 0:
            return 0.0
        return self.unrealized_gain(current_price) / self.cost_basis_total


@dataclass
class Portfolio:
    """Portfolio containing multiple holdings and cash."""

    holdings: list[Holding] = field(default_factory=list)
    cash: float = 0.0

    @classmethod
    def from_json(cls, path: str | Path) -> "Portfolio":
        """Load portfolio from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)

        holdings = [
            Holding(
                ticker=h["ticker"],
                shares=h["shares"],
                cost_basis_per_share=h["cost_basis_per_share"],
            )
            for h in data.get("holdings", [])
        ]

        return cls(holdings=holdings, cash=data.get("cash", 0.0))

    def to_dict(self) -> dict[str, Any]:
        """Convert portfolio to dictionary."""
        return {
            "holdings": [
                {
                    "ticker": h.ticker,
                    "shares": h.shares,
                    "cost_basis_per_share": h.cost_basis_per_share,
                }
                for h in self.holdings
            ],
            "cash": self.cash,
        }

    def get_holding(self, ticker: str) -> Holding | None:
        """Get holding by ticker."""
        for h in self.holdings:
            if h.ticker == ticker:
                return h
        return None

    def get_tickers(self) -> list[str]:
        """Get list of all tickers in portfolio."""
        return [h.ticker for h in self.holdings]

    def total_cost_basis(self) -> float:
        """Total cost basis of all holdings."""
        return sum(h.cost_basis_total for h in self.holdings)

    def total_market_value(self, prices: dict[str, float]) -> float:
        """Calculate total market value including cash.

        Args:
            prices: Dictionary mapping ticker to current price.

        Returns:
            Total portfolio value including cash.
        """
        holdings_value = sum(
            h.market_value(prices.get(h.ticker, 0.0)) for h in self.holdings
        )
        return holdings_value + self.cash

    def get_weights(self, prices: dict[str, float]) -> dict[str, float]:
        """Calculate current portfolio weights.

        Args:
            prices: Dictionary mapping ticker to current price.

        Returns:
            Dictionary mapping ticker to weight (0-1).
        """
        total = self.total_market_value(prices)
        if total == 0:
            return {}

        weights = {}
        for h in self.holdings:
            mv = h.market_value(prices.get(h.ticker, 0.0))
            weights[h.ticker] = mv / total

        # Include cash weight
        weights["_CASH"] = self.cash / total

        return weights

    def get_allocation_by_asset_class(
        self, prices: dict[str, float], ticker_to_asset_class: dict[str, str]
    ) -> dict[str, float]:
        """Get current allocation by asset class.

        Args:
            prices: Current prices for each ticker.
            ticker_to_asset_class: Mapping of ticker to asset class.

        Returns:
            Dictionary mapping asset class to weight.
        """
        total = self.total_market_value(prices)
        if total == 0:
            return {}

        allocations: dict[str, float] = {}
        for h in self.holdings:
            mv = h.market_value(prices.get(h.ticker, 0.0))
            asset_class = ticker_to_asset_class.get(h.ticker, "unknown")
            allocations[asset_class] = allocations.get(asset_class, 0.0) + mv / total

        # Cash is its own asset class
        if self.cash > 0:
            allocations["cash"] = self.cash / total

        return allocations



