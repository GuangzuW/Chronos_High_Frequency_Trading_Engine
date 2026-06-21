import unittest

from services.core.trades import TradeLog


class TradeLogTest(unittest.TestCase):
    def setUp(self):
        # Fixed clock for deterministic timestamps in assertions.
        self.log = TradeLog(clock=lambda: 42)

    def test_record_assigns_monotonic_seq(self):
        a = self.log.record("AAPL", 1, 2, "alice", "bob", 15025, 5000)
        b = self.log.record("AAPL", 3, 4, "carol", "alice", 15030, 1000)
        self.assertEqual(a.seq, 1)
        self.assertEqual(b.seq, 2)
        self.assertEqual(a.ts_ns, 42)

    def test_for_account_matches_buyer_or_seller(self):
        self.log.record("AAPL", 1, 2, "alice", "bob", 15025, 5000)   # alice buys
        self.log.record("AAPL", 3, 4, "carol", "alice", 15030, 1000)  # alice sells
        self.log.record("AAPL", 5, 6, "carol", "bob", 15030, 1000)    # alice absent
        self.assertEqual(len(self.log.for_account("alice")), 2)
        self.assertEqual(len(self.log.for_account("bob")), 2)
        self.assertEqual(len(self.log.for_account("nobody")), 0)

    def test_for_symbol_filters(self):
        self.log.record("AAPL", 1, 2, "a", "b", 1, 1)
        self.log.record("MSFT", 3, 4, "a", "b", 1, 1)
        self.assertEqual(len(self.log.for_symbol("AAPL")), 1)
        self.assertEqual(len(self.log.all()), 2)


if __name__ == "__main__":
    unittest.main()
