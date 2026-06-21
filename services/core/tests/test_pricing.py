import math
import unittest

from services.core import pricing


class PricingTest(unittest.TestCase):
    S, K, t, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.2

    def test_put_call_parity(self):
        c = pricing.black_scholes(self.S, self.K, self.t, self.r, self.sigma, "call")
        p = pricing.black_scholes(self.S, self.K, self.t, self.r, self.sigma, "put")
        # C - P == S - K*e^{-rt}
        self.assertAlmostEqual(c - p, self.S - self.K * math.exp(-self.r * self.t), places=6)

    def test_implied_vol_recovers_input(self):
        price = pricing.black_scholes(self.S, self.K, self.t, self.r, self.sigma, "call")
        iv = pricing.implied_volatility(price, self.S, self.K, self.t, self.r, "call")
        self.assertAlmostEqual(iv, self.sigma, places=4)

    def test_delta_bounds(self):
        gc = pricing.greeks(self.S, self.K, self.t, self.r, self.sigma, "call")
        gp = pricing.greeks(self.S, self.K, self.t, self.r, self.sigma, "put")
        self.assertTrue(0.0 < gc.delta < 1.0)
        self.assertTrue(-1.0 < gp.delta < 0.0)
        self.assertAlmostEqual(gc.delta - gp.delta, 1.0, places=6)  # call delta - put delta = 1
        self.assertGreater(gc.gamma, 0.0)
        self.assertGreater(gc.vega, 0.0)

    def test_intrinsic_at_expiry(self):
        self.assertAlmostEqual(
            pricing.black_scholes(110.0, 100.0, 0.0, self.r, self.sigma, "call"), 10.0, places=6)
        self.assertAlmostEqual(
            pricing.black_scholes(90.0, 100.0, 0.0, self.r, self.sigma, "put"), 10.0, places=6)
        self.assertEqual(
            pricing.black_scholes(90.0, 100.0, 0.0, self.r, self.sigma, "call"), 0.0)


if __name__ == "__main__":
    unittest.main()
