"""Allocation constraints for portfolio optimization."""

from dataclasses import dataclass, field


@dataclass
class AllocationConstraints:
    """Defines constraints for portfolio allocation.

    Attributes:
        asset_class_targets: Target allocation per asset class (e.g., {"equity": 0.8, "bond": 0.2}).
        asset_class_tolerance: Allowed deviation from target (e.g., 0.05 for ±5%).
        min_position_weight: Minimum weight for any single position (0 to allow excluding).
        max_position_weight: Maximum weight for any single position.
        min_positions: Minimum number of positions in portfolio.
        max_positions: Maximum number of positions in portfolio (None for unlimited).
        excluded_tickers: Tickers to exclude from optimization.
        required_tickers: Tickers that must be included in portfolio.
    """

    asset_class_targets: dict[str, float] = field(default_factory=dict)
    asset_class_tolerance: float = 0.05
    min_position_weight: float = 0.0
    max_position_weight: float = 1.0
    min_positions: int = 1
    max_positions: int | None = None
    excluded_tickers: set[str] = field(default_factory=set)
    required_tickers: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Validate constraints."""
        # Ensure targets sum to approximately 1.0
        if self.asset_class_targets:
            total = sum(self.asset_class_targets.values())
            if abs(total - 1.0) > 0.001:
                raise ValueError(
                    f"Asset class targets must sum to 1.0, got {total:.4f}"
                )

        # Validate weight bounds
        if self.min_position_weight < 0:
            raise ValueError("min_position_weight must be >= 0")
        if self.max_position_weight > 1:
            raise ValueError("max_position_weight must be <= 1")
        if self.min_position_weight > self.max_position_weight:
            raise ValueError(
                "min_position_weight must be <= max_position_weight"
            )

    @classmethod
    def from_allocation_string(
        cls,
        allocation_str: str,
        tolerance: float = 0.05,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
    ) -> "AllocationConstraints":
        """Create constraints from allocation string.

        Args:
            allocation_str: String like "equity:0.8,bond:0.2"
            tolerance: Allowed deviation from target.
            min_weight: Minimum position weight.
            max_weight: Maximum position weight.

        Returns:
            AllocationConstraints instance.
        """
        targets = {}
        for pair in allocation_str.split(","):
            asset_class, weight = pair.strip().split(":")
            targets[asset_class.strip()] = float(weight.strip())

        return cls(
            asset_class_targets=targets,
            asset_class_tolerance=tolerance,
            min_position_weight=min_weight,
            max_position_weight=max_weight,
        )

    def get_asset_class_bounds(
        self, asset_class: str
    ) -> tuple[float, float]:
        """Get min/max bounds for an asset class.

        Args:
            asset_class: The asset class to get bounds for.

        Returns:
            Tuple of (min_weight, max_weight) for the asset class.
        """
        target = self.asset_class_targets.get(asset_class, 0.0)
        min_bound = max(0.0, target - self.asset_class_tolerance)
        max_bound = min(1.0, target + self.asset_class_tolerance)
        return (min_bound, max_bound)

    def is_ticker_allowed(self, ticker: str) -> bool:
        """Check if a ticker is allowed in the portfolio.

        Args:
            ticker: The ticker to check.

        Returns:
            True if the ticker is allowed.
        """
        return ticker not in self.excluded_tickers

    def get_position_bounds(self) -> tuple[float, float]:
        """Get min/max bounds for individual positions.

        Returns:
            Tuple of (min_weight, max_weight) for positions.
        """
        return (self.min_position_weight, self.max_position_weight)

    def validate_weights(
        self,
        weights: dict[str, float],
        ticker_to_asset_class: dict[str, str],
    ) -> tuple[bool, list[str]]:
        """Validate if weights satisfy all constraints.

        Args:
            weights: Dictionary mapping ticker to weight.
            ticker_to_asset_class: Mapping of ticker to asset class.

        Returns:
            Tuple of (is_valid, list of violation messages).
        """
        violations = []

        # Check individual position bounds
        for ticker, weight in weights.items():
            if weight > 0:  # Only check active positions
                if weight < self.min_position_weight:
                    violations.append(
                        f"{ticker} weight {weight:.4f} below minimum {self.min_position_weight}"
                    )
                if weight > self.max_position_weight:
                    violations.append(
                        f"{ticker} weight {weight:.4f} above maximum {self.max_position_weight}"
                    )

        # Check excluded tickers
        for ticker in weights:
            if weights[ticker] > 0 and ticker in self.excluded_tickers:
                violations.append(f"{ticker} is excluded but has weight > 0")

        # Check required tickers
        for ticker in self.required_tickers:
            if ticker not in weights or weights[ticker] <= 0:
                violations.append(f"{ticker} is required but not in portfolio")

        # Check asset class targets
        asset_class_weights: dict[str, float] = {}
        for ticker, weight in weights.items():
            if weight > 0:
                ac = ticker_to_asset_class.get(ticker, "unknown")
                asset_class_weights[ac] = asset_class_weights.get(ac, 0.0) + weight

        for ac, target in self.asset_class_targets.items():
            actual = asset_class_weights.get(ac, 0.0)
            min_bound, max_bound = self.get_asset_class_bounds(ac)
            if actual < min_bound:
                violations.append(
                    f"{ac} allocation {actual:.4f} below minimum {min_bound:.4f}"
                )
            if actual > max_bound:
                violations.append(
                    f"{ac} allocation {actual:.4f} above maximum {max_bound:.4f}"
                )

        # Check position count
        active_positions = sum(1 for w in weights.values() if w > 0)
        if active_positions < self.min_positions:
            violations.append(
                f"Only {active_positions} positions, minimum is {self.min_positions}"
            )
        if self.max_positions and active_positions > self.max_positions:
            violations.append(
                f"{active_positions} positions exceeds maximum {self.max_positions}"
            )

        return (len(violations) == 0, violations)

