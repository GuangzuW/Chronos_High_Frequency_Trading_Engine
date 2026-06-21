import unittest
from datetime import date

from services.core.reference_data import ReferenceData


class ReferenceDataTest(unittest.TestCase):
    def setUp(self):
        self.ref = ReferenceData()

    def test_add_and_get_equity(self):
        self.ref.add_equity("AAPL")
        self.assertTrue(self.ref.exists("AAPL"))
        self.assertEqual(self.ref.get("AAPL").kind, "equity")

    def test_unknown_symbol_raises(self):
        with self.assertRaises(KeyError):
            self.ref.get("NOPE")

    def test_symbol_too_long_raises(self):
        with self.assertRaises(ValueError):
            self.ref.add_equity("TOOLONGSYM")

    def test_option_chain_sorted(self):
        self.ref.add_equity("AAPL")
        self.ref.add_option("AAPL_C2", "AAPL", "2026-12-18", 16000, "call")
        self.ref.add_option("AAPL_P1", "AAPL", "2026-06-19", 15000, "put")
        self.ref.add_option("AAPL_C1", "AAPL", "2026-06-19", 15000, "call")
        chain = self.ref.chain("AAPL")
        self.assertEqual([c.symbol for c in chain], ["AAPL_C1", "AAPL_P1", "AAPL_C2"])

    def test_invalid_right_raises(self):
        with self.assertRaises(ValueError):
            self.ref.add_option("X", "AAPL", "2026-06-19", 15000, "neither")

    def test_calendar_weekend_and_holiday(self):
        self.assertFalse(self.ref.is_trading_day(date(2026, 6, 6)))   # Saturday
        self.assertTrue(self.ref.is_trading_day(date(2026, 6, 5)))    # Friday
        self.ref.add_holiday("2026-06-05")
        self.assertFalse(self.ref.is_trading_day(date(2026, 6, 5)))


if __name__ == "__main__":
    unittest.main()
