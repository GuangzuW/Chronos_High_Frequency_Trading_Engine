import unittest

from services.core.surveillance import Surveillance, self_trades
from services.core.trades import TradeRecord


def _t(seq, buyer, seller):
    return TradeRecord(seq, "AAPL", 10, 11, buyer, seller, 15_000, 1_000, 0)


class SurveillanceTest(unittest.TestCase):
    def test_detects_self_trade(self):
        trades = [_t(1, "alice", "bob"), _t(2, "carol", "carol"), _t(3, "x", "y")]
        st = self_trades(trades)
        self.assertEqual([t.seq for t in st], [2])

        report = Surveillance().scan(trades)
        self.assertEqual(report["self_trade_count"], 1)
        self.assertEqual(report["self_trades"][0]["account"], "carol")

    def test_clean_book_has_no_alerts(self):
        report = Surveillance().scan([_t(1, "a", "b"), _t(2, "c", "d")])
        self.assertEqual(report["self_trade_count"], 0)


if __name__ == "__main__":
    unittest.main()
