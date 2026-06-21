"""End-to-end trade lifecycle through the whole core.

Exercises: reference data -> buying-power reservation -> pre-trade risk -> matching venue
-> cash settlement -> position/P&L -> ledger zero-sum invariant. This is the integration
proof that the bounded contexts compose into a working trade.
"""

import unittest

from services.core.ledger import Ledger
from services.core.matching import Venue
from services.core.money import notional_cents
from services.core.oms import OMS, cash_account
from services.core.portfolio import Portfolio
from services.core.reference_data import ReferenceData
from services.core.risk import RiskEngine


class OmsIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.ref = ReferenceData()
        self.ref.add_equity("AAPL")
        self.ledger = Ledger()
        self.risk = RiskEngine()
        self.portfolio = Portfolio()
        self.venue = Venue()
        self.oms = OMS(self.ref, self.ledger, self.risk, self.portfolio, self.venue)

        # Alice has $10,000 cash; Bob holds 10 AAPL @ $140 cost.
        self.ledger.fund(cash_account("alice"), 1_000_000, "fund-alice")  # $10,000
        self.portfolio.seed("bob", "AAPL", qty=10_000, price=14_000)      # 10 units @ $140

    def test_full_match_settles_cash_and_positions(self):
        # Bob rests an ask; Alice's marketable buy crosses it.
        bob = self.oms.place("bob", "AAPL", "sell", price=15_025, qty=10_000)   # 10 @ $150.25
        self.assertEqual(bob.status, "new")
        self.assertEqual(self.venue.book("AAPL").best_ask(), 15_025)

        alice = self.oms.place("alice", "AAPL", "buy", price=15_025, qty=10_000)
        self.assertEqual(alice.status, "filled")
        self.assertEqual(alice.filled, 10_000)
        self.assertEqual(self.oms.get(bob.id).status, "filled")

        notional = notional_cents(15_025, 10_000)  # $1,502.50 -> 150_250 cents
        self.assertEqual(notional, 150_250)

        # Cash moved buyer -> seller.
        self.assertEqual(self.ledger.balance(cash_account("alice")), 1_000_000 - 150_250)
        self.assertEqual(self.ledger.balance(cash_account("bob")), 150_250)

        # No holds left dangling; ledger remains zero-sum.
        self.assertEqual(self.ledger.reserved(cash_account("alice")), 0)
        self.assertEqual(self.ledger.total_balance(), 0)

        # Positions: Alice long 10, Bob flat with realized gain ($150.25-$140)*10 = $102.50.
        self.assertEqual(self.portfolio.position("alice", "AAPL").qty, 10_000)
        self.assertEqual(self.portfolio.position("bob", "AAPL").qty, 0)
        self.assertEqual(self.portfolio.position("bob", "AAPL").realized_cents, 10_250)

    def test_buy_beyond_buying_power_is_rejected_and_releases_hold(self):
        # $10,000 cannot afford 1,000 shares @ $150.25 (= $150,250).
        order = self.oms.place("alice", "AAPL", "buy", price=15_025, qty=1_000_000)
        self.assertEqual(order.status, "rejected")
        self.assertIn("buying power", order.reject_reason)
        self.assertEqual(self.ledger.reserved(cash_account("alice")), 0)  # compensated
        self.assertEqual(self.ledger.available(cash_account("alice")), 1_000_000)

    def test_unknown_instrument_rejected(self):
        order = self.oms.place("alice", "TSLA", "buy", price=10_000, qty=1_000)
        self.assertEqual(order.status, "rejected")
        self.assertIn("unknown instrument", order.reject_reason)

    def test_kill_switch_blocks_new_orders(self):
        self.risk.kill_switch = True
        order = self.oms.place("alice", "AAPL", "buy", price=15_025, qty=1_000)
        self.assertEqual(order.status, "rejected")
        self.assertIn("kill switch", order.reject_reason)
        self.assertEqual(self.ledger.reserved(cash_account("alice")), 0)

    def test_partial_fill_keeps_order_open(self):
        self.oms.place("bob", "AAPL", "sell", price=15_025, qty=4_000)       # only 4 units offered
        alice = self.oms.place("alice", "AAPL", "buy", price=15_025, qty=10_000)
        self.assertEqual(alice.status, "partial")
        self.assertEqual(alice.filled, 4_000)
        self.assertEqual(self.venue.book("AAPL").best_bid(), 15_025)         # remainder rests as bid

    def test_cancel_open_buy_releases_hold_and_removes_from_book(self):
        order = self.oms.place("alice", "AAPL", "buy", price=14_900, qty=10_000)  # rests, no asks
        self.assertEqual(order.status, "new")
        self.assertGreater(self.ledger.reserved(cash_account("alice")), 0)
        self.assertEqual(self.venue.book("AAPL").best_bid(), 14_900)

        canceled = self.oms.cancel(order.id)
        self.assertEqual(canceled.status, "canceled")
        self.assertEqual(self.ledger.reserved(cash_account("alice")), 0)     # hold released
        self.assertIsNone(self.venue.book("AAPL").best_bid())                # pulled from book
        self.assertEqual(self.ledger.available(cash_account("alice")), 1_000_000)

    def test_cancel_partial_keeps_filled_qty(self):
        self.oms.place("bob", "AAPL", "sell", price=15_025, qty=4_000)
        alice = self.oms.place("alice", "AAPL", "buy", price=15_025, qty=10_000)  # fills 4, rests 6
        self.assertEqual(alice.status, "partial")

        canceled = self.oms.cancel(alice.id)
        self.assertEqual(canceled.status, "canceled")
        self.assertEqual(canceled.filled, 4_000)                              # executed qty stays
        self.assertIsNone(self.venue.book("AAPL").best_bid())                 # remainder removed
        self.assertEqual(self.ledger.reserved(cash_account("alice")), 0)
        self.assertEqual(self.portfolio.position("alice", "AAPL").qty, 4_000)

    def test_cancel_resting_sell(self):
        order = self.oms.place("bob", "AAPL", "sell", price=15_025, qty=5_000)
        self.assertEqual(self.venue.book("AAPL").best_ask(), 15_025)
        self.oms.cancel(order.id)
        self.assertIsNone(self.venue.book("AAPL").best_ask())

    def test_cannot_cancel_filled_order(self):
        self.oms.place("bob", "AAPL", "sell", price=15_025, qty=10_000)
        alice = self.oms.place("alice", "AAPL", "buy", price=15_025, qty=10_000)
        self.assertEqual(alice.status, "filled")
        with self.assertRaises(ValueError):
            self.oms.cancel(alice.id)

    def test_cancel_unknown_order_raises(self):
        with self.assertRaises(KeyError):
            self.oms.cancel(999999)

    def test_ioc_partial_then_cancels_remainder(self):
        self.oms.place("bob", "AAPL", "sell", price=15_025, qty=4_000)
        alice = self.oms.place("alice", "AAPL", "buy", price=15_025, qty=10_000, tif="ioc")
        self.assertEqual(alice.filled, 4_000)
        self.assertEqual(alice.status, "canceled")                 # unfilled remainder killed
        self.assertIsNone(self.venue.book("AAPL").best_bid())      # nothing rested
        self.assertEqual(self.ledger.reserved(cash_account("alice")), 0)  # hold fully released

    def test_ioc_full_fill(self):
        self.oms.place("bob", "AAPL", "sell", price=15_025, qty=10_000)
        alice = self.oms.place("alice", "AAPL", "buy", price=15_025, qty=10_000, tif="ioc")
        self.assertEqual(alice.status, "filled")

    def test_ioc_no_liquidity_cancels_with_no_fills(self):
        alice = self.oms.place("alice", "AAPL", "buy", price=15_025, qty=10_000, tif="ioc")
        self.assertEqual(alice.filled, 0)
        self.assertEqual(alice.status, "canceled")
        self.assertIsNone(self.venue.book("AAPL").best_bid())
        self.assertEqual(self.ledger.available(cash_account("alice")), 1_000_000)

    def test_fok_kills_when_insufficient_liquidity(self):
        self.oms.place("bob", "AAPL", "sell", price=15_025, qty=4_000)  # only 4 available
        alice = self.oms.place("alice", "AAPL", "buy", price=15_025, qty=10_000, tif="fok")
        self.assertEqual(alice.status, "canceled")
        self.assertEqual(alice.filled, 0)                          # all-or-nothing: no partial
        self.assertIn("fill-or-kill", alice.reject_reason)
        self.assertEqual(self.venue.book("AAPL").best_ask(), 15_025)  # resting ask untouched
        self.assertEqual(self.ledger.reserved(cash_account("alice")), 0)

    def test_fok_fills_when_sufficient_liquidity(self):
        self.oms.place("bob", "AAPL", "sell", price=15_025, qty=10_000)
        alice = self.oms.place("alice", "AAPL", "buy", price=15_025, qty=10_000, tif="fok")
        self.assertEqual(alice.status, "filled")
        self.assertEqual(alice.filled, 10_000)

    def test_invalid_tif_rejected(self):
        order = self.oms.place("alice", "AAPL", "buy", price=15_025, qty=1_000, tif="bogus")
        self.assertEqual(order.status, "rejected")
        self.assertIn("time-in-force", order.reject_reason)
        self.assertEqual(self.ledger.reserved(cash_account("alice")), 0)  # no hold leaked

    def test_market_buy_fills_at_resting_price(self):
        self.oms.place("bob", "AAPL", "sell", price=15_000, qty=5_000)  # ask $150.00 x5
        alice = self.oms.place("alice", "AAPL", "buy", qty=5_000, order_type="market")
        self.assertEqual(alice.status, "filled")
        self.assertEqual(alice.filled, 5_000)
        self.assertEqual(alice.fills[0].price, 15_000)                  # pays the resting ask
        self.assertEqual(self.portfolio.position("alice", "AAPL").qty, 5_000)

    def test_market_buy_is_cash_bounded(self):
        # alice has $10,000; asks are $150.00. She can afford ~66 units; request 1000.
        self.oms.place("bob", "AAPL", "sell", price=15_000, qty=1_000_000)
        alice = self.oms.place("alice", "AAPL", "buy", qty=1_000_000, order_type="market")
        self.assertEqual(alice.status, "canceled")                      # ran out of cash, didn't rest
        self.assertGreater(alice.filled, 0)
        self.assertGreaterEqual(self.ledger.balance(cash_account("alice")), 0)  # never overspends
        self.assertIsNone(self.venue.book("AAPL").best_bid())           # market never rests

    def test_market_buy_no_liquidity_cancels(self):
        alice = self.oms.place("alice", "AAPL", "buy", qty=5_000, order_type="market")
        self.assertEqual(alice.status, "canceled")
        self.assertEqual(alice.filled, 0)

    def test_market_sell_executes(self):
        self.oms.place("alice", "AAPL", "buy", price=15_000, qty=5_000)  # resting bid
        bob = self.oms.place("bob", "AAPL", "sell", qty=5_000, order_type="market")
        self.assertEqual(bob.status, "filled")
        self.assertEqual(bob.fills[0].price, 15_000)

    def test_market_kill_switch_blocks(self):
        self.risk.kill_switch = True
        order = self.oms.place("alice", "AAPL", "buy", qty=5_000, order_type="market")
        self.assertEqual(order.status, "rejected")
        self.assertIn("kill switch", order.reject_reason)

    def test_invalid_order_type_rejected(self):
        order = self.oms.place("alice", "AAPL", "buy", price=15_000, qty=1_000, order_type="bogus")
        self.assertEqual(order.status, "rejected")
        self.assertIn("order type", order.reject_reason)

    def test_sell_stop_triggers_when_price_falls(self):
        self.ledger.fund(cash_account("mm"), 100_000_000, "f-mm")       # fund the bid maker
        self.oms.place("mm", "AAPL", "buy", price=14_800, qty=100_000)  # deep bid $148
        self.oms.place("mm", "AAPL", "buy", price=15_000, qty=10_000)   # bid $150 x10
        stop = self.oms.place("alice", "AAPL", "sell", qty=10_000,
                              order_type="stop", stop_price=14_900)
        self.assertEqual(stop.status, "pending")                        # no trade yet
        self.oms.place("s1", "AAPL", "sell", price=15_000, qty=10_000)  # trade @150 -> last 15000
        self.assertEqual(self.oms.get(stop.id).status, "pending")       # above stop, still pending
        self.oms.place("s2", "AAPL", "sell", price=14_800, qty=10_000)  # trade @148 -> last 14800
        triggered = self.oms.get(stop.id)
        self.assertEqual(triggered.status, "filled")                    # fired -> market sell
        self.assertEqual(triggered.filled, 10_000)
        self.assertEqual(triggered.fills[0].price, 14_800)

    def test_buy_stop_triggers_when_price_rises(self):
        self.ledger.fund(cash_account("b1"), 100_000_000, "f-b1")        # fund the lifters
        self.ledger.fund(cash_account("b2"), 100_000_000, "f-b2")
        self.oms.place("mm", "AAPL", "sell", price=15_200, qty=100_000)  # deep ask $152
        self.oms.place("mm", "AAPL", "sell", price=15_000, qty=10_000)   # ask $150 x10
        stop = self.oms.place("alice", "AAPL", "buy", qty=10_000,
                              order_type="stop", stop_price=15_100)
        self.assertEqual(stop.status, "pending")
        self.oms.place("b1", "AAPL", "buy", price=15_000, qty=10_000)    # trade @150 -> last 15000
        self.assertEqual(self.oms.get(stop.id).status, "pending")
        self.oms.place("b2", "AAPL", "buy", price=15_200, qty=10_000)    # trade @152 -> last 15200
        triggered = self.oms.get(stop.id)
        self.assertEqual(triggered.status, "filled")
        self.assertEqual(triggered.filled, 10_000)

    def test_stop_limit_rests_when_no_liquidity_on_trigger(self):
        self.ledger.fund(cash_account("b1"), 100_000_000, "f-b1")
        self.oms.place("mm", "AAPL", "sell", price=15_000, qty=5_000)   # ask $150 x5
        sl = self.oms.place("alice", "AAPL", "buy", price=15_000, qty=10_000,
                            order_type="stop_limit", stop_price=15_000)
        self.assertEqual(sl.status, "pending")
        self.oms.place("b1", "AAPL", "buy", price=15_000, qty=5_000)    # consumes the ask, trade @150
        triggered = self.oms.get(sl.id)
        self.assertEqual(triggered.status, "new")                       # became a resting limit bid
        self.assertEqual(self.venue.book("AAPL").best_bid(), 15_000)

    def test_stop_requires_positive_stop_price(self):
        order = self.oms.place("alice", "AAPL", "sell", qty=10_000, order_type="stop", stop_price=0)
        self.assertEqual(order.status, "rejected")
        self.assertIn("stop price", order.reject_reason)

    def test_option_trade_applies_contract_multiplier(self):
        self.ref.add_option("AAPLC", "AAPL", "2026-12-18", 15_000, "call", multiplier=100)
        # bob writes 1 call @ $2.50; alice buys 1. Premium = $2.50 x 100 = $250.
        self.oms.place("bob", "AAPLC", "sell", price=250, qty=1_000)   # 1 contract
        alice = self.oms.place("alice", "AAPLC", "buy", price=250, qty=1_000)
        self.assertEqual(alice.status, "filled")
        # Cash moved is premium x multiplier ($250), not $2.50.
        self.assertEqual(self.ledger.balance(cash_account("alice")), 1_000_000 - 25_000)
        self.assertEqual(self.ledger.balance(cash_account("bob")), 25_000)
        self.assertEqual(self.portfolio.position("alice", "AAPLC").qty, 1_000)   # long 1 contract
        self.assertEqual(self.portfolio.position("bob", "AAPLC").qty, -1_000)    # short 1 contract
        self.assertEqual(self.ledger.total_balance(), 0)

    def test_equity_multiplier_is_one(self):
        # Regression: equities must use multiplier 1 (premium-style multiplier must not leak in).
        self.portfolio.seed("bob", "AAPL", 10_000, 14_000)
        self.oms.place("bob", "AAPL", "sell", price=15_000, qty=10_000)
        self.oms.place("alice", "AAPL", "buy", price=15_000, qty=10_000)
        self.assertEqual(self.ledger.balance(cash_account("alice")), 1_000_000 - 150_000)  # $1500

    def test_trade_recorded_on_fill(self):
        self.portfolio.seed("bob", "AAPL", 10_000, 14_000)
        self.oms.place("bob", "AAPL", "sell", price=15_025, qty=10_000)
        self.oms.place("alice", "AAPL", "buy", price=15_025, qty=10_000)
        trades = self.oms.trades.all()
        self.assertEqual(len(trades), 1)
        t = trades[0]
        self.assertEqual((t.buyer, t.seller), ("alice", "bob"))
        self.assertEqual(t.price, 15_025)
        self.assertEqual(t.qty, 10_000)
        self.assertEqual(self.oms.trades.for_account("alice"), trades)


if __name__ == "__main__":
    unittest.main()
