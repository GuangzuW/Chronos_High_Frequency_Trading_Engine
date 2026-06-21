import unittest

from services.core.market_data import FinnhubProvider, MockProvider


class MockProviderTest(unittest.TestCase):
    def test_stream_normalizes_scaling(self):
        provider = MockProvider([("AAPL", 150.25, 5.0, 111), ("BTC", 65000.50, 0.25, 222)])
        out = list(provider.stream())
        self.assertEqual(out[0].symbol, "AAPL")
        self.assertEqual(out[0].price, 15025)
        self.assertEqual(out[0].quantity, 5000)
        self.assertEqual(out[0].timestamp_ns, 111)
        self.assertEqual(out[1].price, 6500050)
        self.assertEqual(out[1].quantity, 250)


class FinnhubProviderTest(unittest.TestCase):
    def setUp(self):
        self.provider = FinnhubProvider()

    def test_normalizes_mapped_symbols(self):
        msg = {"type": "trade", "data": [
            {"s": "BINANCE:BTCUSDT", "p": 65000.0, "v": 0.5, "t": 1700000000000},
            {"s": "AAPL", "p": 150.25, "v": 10.0, "t": 1700000000000},
        ]}
        out = self.provider.normalize_message(msg)
        self.assertEqual([t.symbol for t in out], ["BTC", "AAPL"])
        self.assertEqual(out[0].price, 6500000)
        self.assertEqual(out[1].price, 15025)
        self.assertEqual(out[1].quantity, 10000)
        self.assertEqual(out[0].timestamp_ns, 1700000000000 * 1_000_000)  # ms -> ns

    def test_skips_unmapped_symbol(self):
        msg = {"type": "trade", "data": [{"s": "UNKNOWN:X", "p": 1.0, "v": 1.0, "t": 0}]}
        self.assertEqual(self.provider.normalize_message(msg), [])

    def test_ignores_non_trade_messages(self):
        self.assertEqual(self.provider.normalize_message({"type": "ping"}), [])

    def test_quantity_floor_is_one(self):
        msg = {"type": "trade", "data": [{"s": "AAPL", "p": 150.0, "v": 0.0, "t": 0}]}
        out = self.provider.normalize_message(msg)
        self.assertEqual(out[0].quantity, 1)  # max(1, ...)


if __name__ == "__main__":
    unittest.main()
