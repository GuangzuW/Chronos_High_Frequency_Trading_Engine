"""Fixed-point money/quantity helpers — the engine's scaling convention, server-side.

Consistent with contracts/WIRE_FORMAT.md and bridge/wire.py:
  price    is scaled x100   (integer cents)
  quantity is scaled x1000  (integer milli-units)
Cash amounts in the ledger are integer cents (minor units) — never floats.
"""

PRICE_SCALE = 100
QUANTITY_SCALE = 1000


def notional_cents(price_scaled: int, qty_scaled: int, multiplier: int = 1) -> int:
    """Cash value (in cents) of `qty_scaled` units at `price_scaled`.

    price (cents) * qty (milli-units) / 1000  ->  cents.
    e.g. 15025 (=$150.25) * 10000 (=10.0) / 1000 = 150250 cents = $1502.50.

    `multiplier` is the contract multiplier (1 for equities, e.g. 100 for an option
    contract): one option at $2.50 premium costs 250 * 1000 * 100 / 1000 = 25000c = $250.
    """
    return price_scaled * qty_scaled * multiplier // QUANTITY_SCALE


def to_price(value: float) -> int:
    return round(value * PRICE_SCALE)


def to_quantity(value: float) -> int:
    return round(value * QUANTITY_SCALE)


def from_cents(cents: int) -> float:
    return cents / PRICE_SCALE
