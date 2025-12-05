"""Transaction cost modeling for portfolio rebalancing."""

from dataclasses import dataclass, field


@dataclass
class TradeOrder:
    """Represents a single trade order.

    Attributes:
        ticker: Ticker symbol.
        shares: Number of shares (positive for buy, negative for sell).
        price: Current price per share.
        value: Absolute dollar value of trade.
    """

    ticker: str
    shares: float
    price: float

    @property
    def value(self) -> float:
        """Absolute dollar value of trade."""
        return abs(self.shares * self.price)

    @property
    def is_buy(self) -> bool:
        """Whether this is a buy order."""
        return self.shares > 0

    @property
    def is_sell(self) -> bool:
        """Whether this is a sell order."""
        return self.shares < 0


@dataclass
class TradeCost:
    """Breakdown of costs for a single trade.

    Attributes:
        ticker: Ticker symbol.
        commission: Fixed commission cost.
        spread_cost: Cost due to bid-ask spread.
        market_impact: Estimated market impact cost.
        total: Total transaction cost.
    """

    ticker: str
    commission: float
    spread_cost: float
    market_impact: float

    @property
    def total(self) -> float:
        """Total transaction cost."""
        return self.commission + self.spread_cost + self.market_impact


@dataclass
class TransactionCostModel:
    """Models transaction costs for portfolio rebalancing.

    Implements a comprehensive cost model including:
    1. Fixed commission per trade
    2. Bid-ask spread (proportional to trade value)
    3. Market impact (for large orders relative to volume)

    Attributes:
        commission_per_trade: Fixed commission per trade in dollars.
        spread_bps: Bid-ask spread in basis points.
        impact_coefficient: Market impact coefficient (typically 0.1-0.5).
        min_trade_value: Minimum trade size to execute.
    """

    commission_per_trade: float = 0.0
    spread_bps: float = 5.0  # 5 basis points = 0.05%
    impact_coefficient: float = 0.1
    min_trade_value: float = 100.0
    avg_daily_volumes: dict[str, int] = field(default_factory=dict)

    def set_volumes(self, volumes: dict[str, int]) -> None:
        """Set average daily volumes for tickers.

        Args:
            volumes: Dictionary mapping ticker to average daily volume.
        """
        self.avg_daily_volumes = volumes

    def calculate_spread_cost(self, trade_value: float) -> float:
        """Calculate cost due to bid-ask spread.

        Args:
            trade_value: Absolute dollar value of trade.

        Returns:
            Spread cost in dollars.
        """
        return trade_value * (self.spread_bps / 10000)

    def calculate_market_impact(
        self,
        trade_value: float,
        ticker: str,
        price: float,
    ) -> float:
        """Calculate market impact cost.

        Uses square-root market impact model:
            Impact = coefficient * sigma * sqrt(Q / V)

        where Q is trade size and V is average daily volume.

        For simplicity, we assume sigma (volatility) is captured in coefficient.

        Args:
            trade_value: Absolute dollar value of trade.
            ticker: Ticker symbol.
            price: Current price per share.

        Returns:
            Market impact cost in dollars.
        """
        adv = self.avg_daily_volumes.get(ticker, 0)

        if adv <= 0 or price <= 0:
            # No volume data, assume minimal impact
            return 0.0

        # Convert to shares
        trade_shares = trade_value / price
        adv_value = adv * price

        # Participation rate
        participation = trade_value / adv_value if adv_value > 0 else 0

        # Square root market impact model
        if participation > 0:
            impact_pct = self.impact_coefficient * (participation ** 0.5)
            return trade_value * impact_pct
        return 0.0

    def calculate_trade_cost(self, order: TradeOrder) -> TradeCost:
        """Calculate total cost for a single trade.

        Args:
            order: Trade order to cost.

        Returns:
            TradeCost breakdown.
        """
        trade_value = order.value

        commission = self.commission_per_trade if trade_value > 0 else 0.0
        spread = self.calculate_spread_cost(trade_value)
        impact = self.calculate_market_impact(
            trade_value, order.ticker, order.price
        )

        return TradeCost(
            ticker=order.ticker,
            commission=commission,
            spread_cost=spread,
            market_impact=impact,
        )

    def calculate_total_costs(
        self, orders: list[TradeOrder]
    ) -> tuple[list[TradeCost], float]:
        """Calculate total costs for a list of trades.

        Args:
            orders: List of trade orders.

        Returns:
            Tuple of (list of TradeCost, total cost).
        """
        costs = [self.calculate_trade_cost(order) for order in orders]
        total = sum(c.total for c in costs)
        return costs, total

    def filter_small_trades(
        self, orders: list[TradeOrder]
    ) -> list[TradeOrder]:
        """Filter out trades below minimum value threshold.

        Args:
            orders: List of trade orders.

        Returns:
            Filtered list with only significant trades.
        """
        return [o for o in orders if o.value >= self.min_trade_value]

    def calculate_annual_expense_drag(
        self,
        portfolio_value: float,
        expense_ratios: dict[str, float],
        weights: dict[str, float],
    ) -> float:
        """Calculate annual expense ratio drag on portfolio.

        Args:
            portfolio_value: Total portfolio value.
            expense_ratios: Mapping of ticker to expense ratio.
            weights: Portfolio weights by ticker.

        Returns:
            Annual expense cost in dollars.
        """
        weighted_expense = sum(
            weights.get(ticker, 0) * expense_ratios.get(ticker, 0)
            for ticker in weights
        )
        return portfolio_value * weighted_expense

    def calculate_rebalancing_trades(
        self,
        current_weights: dict[str, float],
        target_weights: dict[str, float],
        portfolio_value: float,
        prices: dict[str, float],
    ) -> list[TradeOrder]:
        """Calculate trades needed to rebalance portfolio.

        Args:
            current_weights: Current portfolio weights.
            target_weights: Target portfolio weights.
            portfolio_value: Total portfolio value (excluding cash).
            prices: Current prices by ticker.

        Returns:
            List of trade orders to execute.
        """
        orders = []

        # Get all tickers
        all_tickers = set(current_weights.keys()) | set(target_weights.keys())
        all_tickers.discard("_CASH")  # Exclude cash

        for ticker in all_tickers:
            current_weight = current_weights.get(ticker, 0.0)
            target_weight = target_weights.get(ticker, 0.0)

            weight_diff = target_weight - current_weight
            value_diff = weight_diff * portfolio_value

            if abs(value_diff) < 0.01:
                continue

            price = prices.get(ticker, 0.0)
            if price <= 0:
                continue

            shares = value_diff / price

            orders.append(
                TradeOrder(
                    ticker=ticker,
                    shares=shares,
                    price=price,
                )
            )

        return orders

    def net_benefit_of_rebalancing(
        self,
        current_weights: dict[str, float],
        target_weights: dict[str, float],
        portfolio_value: float,
        prices: dict[str, float],
        expected_return_improvement: float,
        holding_period_years: float = 1.0,
    ) -> dict[str, float]:
        """Analyze whether rebalancing is worth the transaction costs.

        Args:
            current_weights: Current portfolio weights.
            target_weights: Target portfolio weights.
            portfolio_value: Total portfolio value.
            prices: Current prices.
            expected_return_improvement: Expected improvement in annual return.
            holding_period_years: Expected holding period.

        Returns:
            Dictionary with cost-benefit analysis.
        """
        orders = self.calculate_rebalancing_trades(
            current_weights, target_weights, portfolio_value, prices
        )
        orders = self.filter_small_trades(orders)
        _, total_cost = self.calculate_total_costs(orders)

        # Expected benefit from improved allocation
        expected_benefit = (
            portfolio_value * expected_return_improvement * holding_period_years
        )

        return {
            "transaction_cost": total_cost,
            "expected_benefit": expected_benefit,
            "net_benefit": expected_benefit - total_cost,
            "cost_as_pct_of_portfolio": total_cost / portfolio_value * 100
            if portfolio_value > 0
            else 0,
            "breakeven_holding_period": total_cost
            / (portfolio_value * expected_return_improvement)
            if expected_return_improvement > 0
            else float("inf"),
            "recommend_rebalance": expected_benefit > total_cost,
        }

