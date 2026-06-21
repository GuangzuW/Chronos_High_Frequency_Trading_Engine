import unittest

from services.core.corporate_actions import CorporateActions
from services.core.ledger import Ledger
from services.core.oms import cash_account
from services.core.portfolio import Portfolio


class CorporateActionsTest(unittest.TestCase):
    def setUp(self):
        self.pf = Portfolio()
        self.led = Ledger()
        self.ca = CorporateActions(self.pf, self.led)

    def test_forward_split_scales_qty_keeps_cost(self):
        self.pf.seed("alice", "AAPL", 10_000, 15_000)   # 10 shares, cost = $1500
        before_cost = self.pf.position("alice", "AAPL").cost_cents
        self.ca.split("AAPL", 2, 1)
        p = self.pf.position("alice", "AAPL")
        self.assertEqual(p.qty, 20_000)                 # 2:1 -> doubled
        self.assertEqual(p.cost_cents, before_cost)     # basis unchanged (cost/share halves)

    def test_dividend_credits_long_holders(self):
        self.pf.seed("alice", "AAPL", 10_000, 15_000)   # 10 shares
        paid = self.ca.dividend("AAPL", 50)             # $0.50/share x 10 = $5.00
        self.assertEqual(self.led.balance(cash_account("alice")), 500)
        self.assertEqual(paid, [("alice", 500)])

    def test_invalid_ratios_raise(self):
        with self.assertRaises(ValueError):
            self.ca.split("AAPL", 0)
        with self.assertRaises(ValueError):
            self.ca.dividend("AAPL", -1)


if __name__ == "__main__":
    unittest.main()
