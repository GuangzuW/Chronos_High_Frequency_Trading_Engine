import unittest

from services.core.ohlc import build_bars


class OhlcTest(unittest.TestCase):
    def test_bucketing_ohlcv(self):
        ticks = [(0, 100, 5), (500, 110, 3), (999, 90, 2), (1000, 120, 1), (1500, 130, 4)]
        bars = build_bars(ticks, bucket_ns=1000)
        self.assertEqual(len(bars), 2)
        b0, b1 = bars
        self.assertEqual((b0["open"], b0["high"], b0["low"], b0["close"], b0["volume"]),
                         (100, 110, 90, 90, 10))
        self.assertEqual((b1["open"], b1["high"], b1["low"], b1["close"], b1["volume"]),
                         (120, 130, 120, 130, 5))
        self.assertLess(b0["start"], b1["start"])  # sorted by time

    def test_invalid_bucket_raises(self):
        with self.assertRaises(ValueError):
            build_bars([], 0)


if __name__ == "__main__":
    unittest.main()
