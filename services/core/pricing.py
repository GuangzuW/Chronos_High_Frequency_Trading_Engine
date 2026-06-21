"""Pricing / Analytics (Phase 6.1) — Black-Scholes, Greeks, implied volatility.

Pure math (stdlib only). Prices/strikes here are plain floats (analytics domain), not the
engine's fixed-point integers — callers convert at the boundary.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_SQRT_2PI = math.sqrt(2.0 * math.pi)


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT_2PI


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


@dataclass
class Greeks:
    price: float
    delta: float
    gamma: float
    vega: float    # per 1.00 (100%) change in vol
    theta: float   # per year
    rho: float     # per 1.00 (100%) change in rate


def _d1_d2(S: float, K: float, t: float, r: float, sigma: float) -> tuple[float, float]:
    vol_sqrt_t = sigma * math.sqrt(t)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * t) / vol_sqrt_t
    d2 = d1 - vol_sqrt_t
    return d1, d2


def black_scholes(S: float, K: float, t: float, r: float, sigma: float, right: str) -> float:
    """European option price. right in {'call','put'}."""
    if t <= 0 or sigma <= 0:
        # Intrinsic value at/after expiry or with no vol.
        intrinsic = (S - K) if right == "call" else (K - S)
        return max(0.0, intrinsic)
    d1, d2 = _d1_d2(S, K, t, r, sigma)
    disc = math.exp(-r * t)
    if right == "call":
        return S * _norm_cdf(d1) - K * disc * _norm_cdf(d2)
    elif right == "put":
        return K * disc * _norm_cdf(-d2) - S * _norm_cdf(-d1)
    raise ValueError("right must be 'call' or 'put'")


def greeks(S: float, K: float, t: float, r: float, sigma: float, right: str) -> Greeks:
    price = black_scholes(S, K, t, r, sigma, right)
    if t <= 0 or sigma <= 0:
        return Greeks(price=price, delta=0.0, gamma=0.0, vega=0.0, theta=0.0, rho=0.0)
    d1, d2 = _d1_d2(S, K, t, r, sigma)
    disc = math.exp(-r * t)
    pdf = _norm_pdf(d1)
    gamma = pdf / (S * sigma * math.sqrt(t))
    vega = S * pdf * math.sqrt(t)
    if right == "call":
        delta = _norm_cdf(d1)
        theta = (-S * pdf * sigma / (2 * math.sqrt(t))) - r * K * disc * _norm_cdf(d2)
        rho = K * t * disc * _norm_cdf(d2)
    else:
        delta = _norm_cdf(d1) - 1.0
        theta = (-S * pdf * sigma / (2 * math.sqrt(t))) + r * K * disc * _norm_cdf(-d2)
        rho = -K * t * disc * _norm_cdf(-d2)
    return Greeks(price=price, delta=delta, gamma=gamma, vega=vega, theta=theta, rho=rho)


def implied_volatility(market_price: float, S: float, K: float, t: float, r: float,
                       right: str, tol: float = 1e-6, max_iter: int = 100) -> float:
    """Solve for sigma via bisection. Returns nan if not bracketable."""
    lo, hi = 1e-6, 5.0
    p_lo = black_scholes(S, K, t, r, lo, right) - market_price
    p_hi = black_scholes(S, K, t, r, hi, right) - market_price
    if p_lo * p_hi > 0:
        return float("nan")
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        p_mid = black_scholes(S, K, t, r, mid, right) - market_price
        if abs(p_mid) < tol:
            return mid
        if p_lo * p_mid < 0:
            hi = mid
        else:
            lo, p_lo = mid, p_mid
    return 0.5 * (lo + hi)
