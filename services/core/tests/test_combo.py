import unittest

from services.core.ledger import Ledger
from services.core.matching import Venue
from services.core.oms import OMS, cash_account
from services.core.portfolio import Portfolio
from services.core.reference_data import ReferenceData
from services.core.risk import RiskEngine


class ComboTest(unittest.TestCase):
    def setUp(self):
        self.ref = ReferenceData()
        self.ref.add_option("C150", "AAPL", "2026-12-18", 15_000, "call", multiplier=100)
        self.ref.add_option("C160", "AAPL", "2026-12-18", 16_000, "call", multiplier=100)
        self.ledger = Ledger()
        self.risk = RiskEngine()
        self.pf = Portfolio()
        self.venue = Venue()
        self.oms = OMS(self.ref, self.ledger, self.risk, self.pf, self.venue)
        self.ledger.fund(cash_account("alice"), 10_000_000, "f")  # $100k

    def test_combo_fills_all_legs_atomically(self):
        self.oms.place("w1", "C150", "sell", price=500, qty=1_000)   # ask $5.00 x1
        self.oms.place("w2", "C160", "sell", price=200, qty=1_000)   # ask $2.00 x1
        res = self.oms.place_combo("alice", [
            {"symbol": "C150", "side": "buy", "price": 500, "qty": 1_000},
            {"symbol": "C160", "side": "buy", "price": 200, "qty": 1_000},
        ])
        self.assertEqual(res["status"], "filled")
        self.assertEqual(len(res["legs"]), 2)
        self.assertEqual(self.pf.position("alice", "C150").qty, 1_000)
        self.assertEqual(self.pf.position("alice", "C160").qty, 1_000)
        # Premium with multiplier: ($5 + $2) x 100 = $700.
        self.assertEqual(self.ledger.balance(cash_account("alice")), 10_000_000 - 70_000)

    def test_combo_rejected_atomically_when_a_leg_unfillable(self):
        self.oms.place("w1", "C150", "sell", price=500, qty=1_000)   # only one leg has liquidity
        res = self.oms.place_combo("alice", [
            {"symbol": "C150", "side": "buy", "price": 500, "qty": 1_000},
            {"symbol": "C160", "side": "buy", "price": 200, "qty": 1_000},  # no asks
        ])
        self.assertEqual(res["status"], "rejected")
        self.assertEqual(res["legs"], [])
        self.assertEqual(self.pf.position("alice", "C150").qty, 0)  # no leg executed


if __name__ == "__main__":
    unittest.main()
