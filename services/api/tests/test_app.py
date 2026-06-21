import unittest

from services.api.app import TradingApp
from services.core.money import to_price, to_quantity


class TradingAppTest(unittest.TestCase):
    def setUp(self):
        self.app = TradingApp()
        self.app.add_equity("AAPL")
        self.app.fund("alice", 10_000.0)

    def test_fund_and_balance(self):
        b = self.app.balance("alice")
        self.assertEqual(b["cash"], 10_000.0)
        self.assertEqual(b["available"], 10_000.0)

    def test_end_to_end_trade(self):
        # Bob holds 10 AAPL @ $140; he sells 10 @ $150.25; Alice buys 10 @ $150.25.
        self.app.portfolio.seed("bob", "AAPL", to_quantity(10), to_price(140))
        sell = self.app.place_order("bob", "AAPL", "sell", 150.25, 10)
        self.assertEqual(sell["status"], "new")

        buy = self.app.place_order("alice", "AAPL", "buy", 150.25, 10)
        self.assertEqual(buy["status"], "filled")
        self.assertEqual(buy["filled"], 10.0)
        self.assertEqual(len(buy["fills"]), 1)
        self.assertEqual(buy["fills"][0]["price"], 150.25)

        self.assertEqual(self.app.balance("alice")["cash"], 10_000.0 - 1_502.50)
        self.assertEqual(self.app.balance("bob")["cash"], 1_502.50)

        pos = {p["symbol"]: p for p in self.app.positions("alice")["positions"]}
        self.assertEqual(pos["AAPL"]["quantity"], 10.0)
        bobpos = {p["symbol"]: p for p in self.app.positions("bob")["positions"]}
        self.assertEqual(bobpos["AAPL"]["realized_pnl"], 102.50)

    def test_reject_insufficient_buying_power(self):
        o = self.app.place_order("alice", "AAPL", "buy", 150.25, 1000)  # ~$150k
        self.assertEqual(o["status"], "rejected")
        self.assertIn("buying power", o["reject_reason"])

    def test_option_chain_and_pricing(self):
        self.app.add_option("AAPL_C", "AAPL", "2026-06-19", 150.0, "call")
        chain = self.app.chain("AAPL")
        self.assertEqual(chain[0]["strike"], 150.0)
        g = self.app.price_option(100.0, 100.0, 1.0, 0.05, 0.2, "call")
        self.assertGreater(g["price"], 0.0)
        self.assertTrue(0.0 < g["delta"] < 1.0)

    def test_book_depth(self):
        self.app.place_order("alice", "AAPL", "buy", 149.00, 5)  # rests as a bid
        book = self.app.book("AAPL")
        self.assertEqual(book["bids"][0]["price"], 149.00)
        self.assertEqual(book["bids"][0]["quantity"], 5.0)


if __name__ == "__main__":
    unittest.main()
