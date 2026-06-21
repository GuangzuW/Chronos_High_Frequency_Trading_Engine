import unittest

from services.core.ledger import Ledger
from services.core.oms import cash_account
from services.core.portfolio import Portfolio
from services.core.statements import account_statement
from services.core.trades import TradeLog


class StatementTest(unittest.TestCase):
    def test_statement_reconciles_cash_trades_positions(self):
        led = Ledger()
        led.fund(cash_account("alice"), 100_000, "f1")
        tl = TradeLog(clock=lambda: 0)
        tl.record("AAPL", 1, 2, "alice", "bob", 15_000, 1_000)
        pf = Portfolio()
        pf.seed("alice", "AAPL", 1_000, 15_000)

        s = account_statement("alice", led, tl, pf)
        self.assertEqual(s["account"], "alice")
        self.assertEqual(s["ending_cash_cents"], 100_000)
        self.assertEqual(len(s["cash_postings"]), 1)
        self.assertEqual(len(s["trades"]), 1)
        self.assertEqual(s["trades"][0]["side"], "buy")
        self.assertEqual(s["positions"][0]["symbol"], "AAPL")


if __name__ == "__main__":
    unittest.main()
