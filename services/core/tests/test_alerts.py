import unittest

from services.core.alerts import AlertEngine


class AlertEngineTest(unittest.TestCase):
    def test_above_alert_fires_once(self):
        e = AlertEngine()
        e.add("alice", "AAPL", "above", 15_000)
        self.assertEqual(e.on_trade("AAPL", 14_900), [])      # below threshold
        fired = e.on_trade("AAPL", 15_000)                    # reaches threshold
        self.assertEqual(len(fired), 1)
        self.assertEqual(e.on_trade("AAPL", 15_100), [])      # one-shot: already fired
        self.assertEqual(len(e.fired_for("alice")), 1)
        self.assertEqual(e.armed_for("alice"), [])

    def test_below_alert_and_symbol_filter(self):
        e = AlertEngine()
        e.add("bob", "BTC", "below", 1_000)
        self.assertEqual(e.on_trade("AAPL", 500), [])         # different symbol
        self.assertEqual(len(e.on_trade("BTC", 1_000)), 1)

    def test_invalid_op_raises(self):
        with self.assertRaises(ValueError):
            AlertEngine().add("a", "X", "sideways", 1)


if __name__ == "__main__":
    unittest.main()
