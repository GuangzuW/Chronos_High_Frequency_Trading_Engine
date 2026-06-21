import unittest

from services.core.matching import OrderBook
from services.core.money import notional_cents as notional


class MatchingTest(unittest.TestCase):
    def setUp(self):
        self.book = OrderBook()

    def test_resting_order_sets_best_prices(self):
        fills, remaining = self.book.add_limit(1, "buy", 10000, 5000)
        self.assertEqual(fills, [])
        self.assertEqual(remaining, 5000)
        self.assertEqual(self.book.best_bid(), 10000)
        self.assertIsNone(self.book.best_ask())

    def test_full_cross_executes_at_resting_price(self):
        self.book.add_limit(1, "sell", 10000, 5000)        # ask rests
        fills, remaining = self.book.add_limit(2, "buy", 10100, 5000)  # marketable buy
        self.assertEqual(remaining, 0)
        self.assertEqual(len(fills), 1)
        self.assertEqual(fills[0].buy_order_id, 2)
        self.assertEqual(fills[0].sell_order_id, 1)
        self.assertEqual(fills[0].price, 10000)            # passive (resting) ask price
        self.assertEqual(fills[0].qty, 5000)

    def test_non_marketable_does_not_cross(self):
        self.book.add_limit(1, "sell", 10100, 5000)
        fills, remaining = self.book.add_limit(2, "buy", 10000, 5000)
        self.assertEqual(fills, [])
        self.assertEqual(remaining, 5000)

    def test_partial_fill_rests_remainder(self):
        self.book.add_limit(1, "sell", 10000, 2000)
        fills, remaining = self.book.add_limit(2, "buy", 10000, 5000)
        self.assertEqual(sum(f.qty for f in fills), 2000)
        self.assertEqual(remaining, 3000)
        self.assertEqual(self.book.best_bid(), 10000)

    def test_fifo_within_price_level(self):
        self.book.add_limit(1, "sell", 10000, 2000)  # first in
        self.book.add_limit(2, "sell", 10000, 2000)  # second in
        fills, _ = self.book.add_limit(3, "buy", 10000, 3000)
        self.assertEqual(fills[0].sell_order_id, 1)   # order 1 fills first
        self.assertEqual(fills[0].qty, 2000)
        self.assertEqual(fills[1].sell_order_id, 2)
        self.assertEqual(fills[1].qty, 1000)

    def test_add_limit_without_resting_drops_remainder(self):
        self.book.add_limit(1, "sell", 10000, 2000)
        fills, remaining = self.book.add_limit(2, "buy", 10000, 5000, rest_remainder=False)
        self.assertEqual(sum(f.qty for f in fills), 2000)
        self.assertEqual(remaining, 3000)
        self.assertIsNone(self.book.best_bid())  # remainder NOT rested

    def test_fillable_qty(self):
        self.book.add_limit(1, "sell", 10000, 2000)
        self.book.add_limit(2, "sell", 10100, 3000)
        self.assertEqual(self.book.fillable_qty("buy", 10000), 2000)   # only the cheaper level crosses
        self.assertEqual(self.book.fillable_qty("buy", 10100), 5000)   # both levels cross
        self.assertEqual(self.book.fillable_qty("buy", 9000), 0)       # nothing crosses

    def test_price_priority_sweeps_cheapest_first(self):
        self.book.add_limit(1, "sell", 10100, 2000)
        self.book.add_limit(2, "sell", 10000, 2000)   # cheaper -> better
        fills, _ = self.book.add_limit(3, "buy", 10100, 3000)
        self.assertEqual(fills[0].price, 10000)        # cheapest ask first
        self.assertEqual(fills[1].price, 10100)

    def test_market_buy_unbounded_sweeps_all_levels(self):
        self.book.add_limit(1, "sell", 10000, 2000)
        self.book.add_limit(2, "sell", 10100, 2000)
        fills, remaining, spent = self.book.match_market(3, "buy", 5000)
        self.assertEqual(sum(f.qty for f in fills), 4000)
        self.assertEqual(remaining, 1000)             # no more liquidity; nothing rests
        self.assertEqual(spent, notional(10000, 2000) + notional(10100, 2000))

    def test_market_buy_is_cash_bounded(self):
        self.book.add_limit(1, "sell", 10000, 100_000)   # plenty of liquidity ($100/unit)
        budget = 100_000                                  # $1000 -> affords 10 units (10_000 scaled)
        fills, remaining, spent = self.book.match_market(2, "buy", 50_000, budget_cents=budget)
        self.assertEqual(sum(f.qty for f in fills), 10_000)
        self.assertEqual(remaining, 40_000)
        self.assertLessEqual(spent, budget)
        self.assertEqual(spent, notional(10000, 10_000))

    def test_market_sell_sweeps_bids(self):
        self.book.add_limit(1, "buy", 10000, 3000)
        fills, remaining, spent = self.book.match_market(2, "sell", 3000)
        self.assertEqual(remaining, 0)
        self.assertEqual(fills[0].price, 10000)


if __name__ == "__main__":
    unittest.main()
