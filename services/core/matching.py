"""Matching venue (Phase 3) — price-time-priority limit order book.

A faithful Python mirror of the C++ engine's logic in include/chronos/limit_order_book.hpp:
bids sorted high->low, asks low->high, FIFO within a price level, marketable orders sweep
opposite levels and the residual rests. Lets the full trade lifecycle run end-to-end in
tests without the compiled C++ binary; the C++ engine remains the production hot path.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.core.money import QUANTITY_SCALE, notional_cents


@dataclass
class Fill:
    buy_order_id: int
    sell_order_id: int
    price: int   # scaled (execution price = resting/passive order's price)
    qty: int     # scaled


class OrderBook:
    def __init__(self) -> None:
        # price -> FIFO list of [order_id, remaining_qty]
        self._bids: dict[int, list[list[int]]] = {}
        self._asks: dict[int, list[list[int]]] = {}

    def best_bid(self):
        return max(self._bids) if self._bids else None

    def best_ask(self):
        return min(self._asks) if self._asks else None

    def depth(self):
        bids = sorted(((p, sum(e[1] for e in lv)) for p, lv in self._bids.items()), reverse=True)
        asks = sorted((p, sum(e[1] for e in lv)) for p, lv in self._asks.items())
        return bids, asks

    def remove(self, order_id: int, side: str, price: int) -> bool:
        """Remove a resting order from the book (used by cancellation). Returns True if found."""
        book = self._bids if side == "buy" else self._asks
        level = book.get(price)
        if not level:
            return False
        for i, entry in enumerate(level):
            if entry[0] == order_id:
                level.pop(i)
                if not level:
                    del book[price]
                return True
        return False

    def rest(self, order_id: int, side: str, price: int, qty: int) -> None:
        """Insert a resting order directly WITHOUT matching.

        Used to rebuild the open book from persisted orders on restart, so re-inserting
        does not generate spurious fills against other restored orders.
        """
        book = self._bids if side == "buy" else self._asks
        book.setdefault(price, []).append([order_id, qty])

    def fillable_qty(self, side: str, price: int) -> int:
        """Total opposite-side quantity that would cross an order of the given side/price.

        Used by fill-or-kill to decide up front whether the whole order can execute now.
        """
        total = 0
        if side == "buy":
            for ask_price, level in self._asks.items():
                if ask_price <= price:
                    total += sum(e[1] for e in level)
        else:
            for bid_price, level in self._bids.items():
                if bid_price >= price:
                    total += sum(e[1] for e in level)
        return total

    def add_limit(self, order_id: int, side: str, price: int, qty: int,
                  rest_remainder: bool = True) -> tuple[list[Fill], int]:
        """Match an incoming limit order; return (fills, remaining_qty).

        If rest_remainder is False (IOC/FOK/market-style), any unfilled quantity is dropped
        instead of resting in the book.
        """
        if side not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        if price <= 0 or qty <= 0:
            raise ValueError("price and qty must be positive")

        fills: list[Fill] = []
        remaining = qty

        if side == "buy":
            while remaining > 0 and self._asks:
                best = min(self._asks)
                if price < best:  # not marketable
                    break
                level = self._asks[best]
                while remaining > 0 and level:
                    entry = level[0]
                    m = min(remaining, entry[1])
                    fills.append(Fill(order_id, entry[0], best, m))
                    remaining -= m
                    entry[1] -= m
                    if entry[1] == 0:
                        level.pop(0)
                if not level:
                    del self._asks[best]
            if remaining > 0 and rest_remainder:
                self._bids.setdefault(price, []).append([order_id, remaining])
        else:  # sell
            while remaining > 0 and self._bids:
                best = max(self._bids)
                if price > best:
                    break
                level = self._bids[best]
                while remaining > 0 and level:
                    entry = level[0]
                    m = min(remaining, entry[1])
                    fills.append(Fill(entry[0], order_id, best, m))
                    remaining -= m
                    entry[1] -= m
                    if entry[1] == 0:
                        level.pop(0)
                if not level:
                    del self._bids[best]
            if remaining > 0 and rest_remainder:
                self._asks.setdefault(price, []).append([order_id, remaining])

        return fills, remaining


    def match_market(self, order_id: int, side: str, qty: int,
                     budget_cents: int | None = None, multiplier: int = 1) -> tuple[list[Fill], int, int]:
        """Match a market order: sweep the opposite book with no price limit. Never rests.

        Returns (fills, remaining_qty, spent_cents). For buys, budget_cents caps total spend
        (cash-bounded) so a market buy can never overspend available cash — when the budget
        runs out the rest is left unfilled (to be canceled by the caller).
        """
        fills: list[Fill] = []
        remaining = qty
        spent = 0

        if side == "buy":
            while remaining > 0 and self._asks:
                best = min(self._asks)
                level = self._asks[best]
                while remaining > 0 and level:
                    entry = level[0]
                    m = min(remaining, entry[1])
                    if budget_cents is not None:
                        affordable = (budget_cents - spent) * QUANTITY_SCALE // (best * multiplier)
                        if affordable <= 0:
                            return fills, remaining, spent  # budget exhausted
                        m = min(m, affordable)
                    fills.append(Fill(order_id, entry[0], best, m))
                    spent += notional_cents(best, m, multiplier)
                    remaining -= m
                    entry[1] -= m
                    if entry[1] == 0:
                        level.pop(0)
                if not level:
                    del self._asks[best]
        else:  # sell — proceeds only, no budget constraint
            while remaining > 0 and self._bids:
                best = max(self._bids)
                level = self._bids[best]
                while remaining > 0 and level:
                    entry = level[0]
                    m = min(remaining, entry[1])
                    fills.append(Fill(entry[0], order_id, best, m))
                    spent += notional_cents(best, m)
                    remaining -= m
                    entry[1] -= m
                    if entry[1] == 0:
                        level.pop(0)
                if not level:
                    del self._bids[best]

        return fills, remaining, spent


class Venue:
    """Symbol-sharded set of order books (mirrors ShardedMatchingEngine)."""

    def __init__(self) -> None:
        self._books: dict[str, OrderBook] = {}

    def book(self, symbol: str) -> OrderBook:
        return self._books.setdefault(symbol, OrderBook())
