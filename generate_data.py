#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy>=1.24.0",
#   "pandas>=2.0.0",
#   "scipy>=1.10.0",
# ]
# ///
"""
Generates realistic synthetic price data for SOXX, QQQ, SOXL, TQQQ
based on their known statistical characteristics and correlations.
Outputs docs/data.json consumed by the Angular dashboard.

ETF characteristics used:
  QQQ   – NASDAQ-100 ETF, base reference
  SOXX  – Semiconductor ETF, ~1.2x QQQ beta, higher vol
  SOXL  – 3× Semiconductor (Direxion), ~3× SOXX daily moves + leverage decay
  TQQQ  – 3× NASDAQ-100 (ProShares), ~3× QQQ daily moves + leverage decay
"""

import json
import math
import os
from datetime import date, timedelta

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

# ── Seed for reproducibility ──────────────────────────────────────────────────
RNG = np.random.default_rng(42)

TICKERS   = ["SOXX", "QQQ", "SOXL", "TQQQ"]
BENCHMARK = "SPY"

# ── Current approximate prices (late 2025 / early 2026) ──────────────────────
CURRENT_PRICES = {
    "QQQ":  476.32,
    "SOXX": 224.18,
    "SOXL":  32.75,
    "TQQQ":  71.40,
    "SPY":  568.90,
}

# ── Daily return parameters ───────────────────────────────────────────────────
# Drift and volatility calibrated from historical data
DAILY_PARAMS = {
    #          mu_daily   sigma_daily
    "SPY":  (0.00045,    0.0100),   # ~11% ann return, ~16% vol
    "QQQ":  (0.00065,    0.0130),   # ~16% ann return, ~21% vol
    "SOXX": (0.00075,    0.0165),   # ~19% ann return, ~26% vol
    "SOXL": (0.00060,    0.0480),   # leveraged, ~75% vol (decay reduces drift)
    "TQQQ": (0.00055,    0.0380),   # leveraged, ~60% vol
}

# ── Cholesky correlation structure ───────────────────────────────────────────
# Order: SPY, QQQ, SOXX, SOXL, TQQQ
CORR = np.array([
    # SPY    QQQ    SOXX   SOXL   TQQQ
    [1.000, 0.940, 0.860, 0.780, 0.890],   # SPY
    [0.940, 1.000, 0.890, 0.820, 0.970],   # QQQ
    [0.860, 0.890, 1.000, 0.960, 0.840],   # SOXX
    [0.780, 0.820, 0.960, 1.000, 0.790],   # SOXL
    [0.890, 0.970, 0.840, 0.790, 1.000],   # TQQQ
])

ORDER = ["SPY", "QQQ", "SOXX", "SOXL", "TQQQ"]

# ── Helpers ───────────────────────────────────────────────────────────────────
def safe(v):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    return round(float(v), 6)

def trading_days(n=504):
    """Return a list of n trading days ending today (skips weekends)."""
    end   = date(2026, 5, 9)   # last trading day before this session
    days  = []
    d     = end
    while len(days) < n:
        if d.weekday() < 5:    # Mon–Fri
            days.append(d)
        d -= timedelta(days=1)
    return list(reversed(days))

def simulate_prices(n=504):
    """Simulate correlated log-normal price paths."""
    L = np.linalg.cholesky(CORR)
    # Draw n iid standard-normal vectors of length 5 (one per ticker)
    Z = RNG.standard_normal((n, len(ORDER)))
    corr_Z = Z @ L.T                       # shape (n, 5)

    prices = {}
    for i, ticker in enumerate(ORDER):
        mu, sigma = DAILY_PARAMS[ticker]
        log_ret   = mu - 0.5 * sigma**2 + sigma * corr_Z[:, i]
        # Back-fill: compute history so that index[-1] matches CURRENT_PRICES
        cumulative = np.exp(np.cumsum(log_ret))
        scale      = CURRENT_PRICES[ticker] / cumulative[-1]
        prices[ticker] = cumulative * scale

    return prices

def pct_change(arr):
    return np.diff(arr) / arr[:-1]

def annualized_return(returns, periods=252):
    total = np.prod(1 + returns)
    n = len(returns)
    if n == 0:
        return None
    return float(total ** (periods / n) - 1)

def annualized_vol(returns, periods=252):
    return float(np.std(returns, ddof=1) * np.sqrt(periods))

def sharpe(returns, rf=0.05, periods=252):
    ar = annualized_return(returns, periods)
    av = annualized_vol(returns, periods)
    if ar is None or av == 0:
        return None
    return (ar - rf) / av

def max_drawdown(prices):
    roll_max = np.maximum.accumulate(prices)
    dd = (prices - roll_max) / roll_max
    return float(np.min(dd))

def beta_calc(asset_rets, bench_rets):
    cov  = np.cov(asset_rets, bench_rets)
    if cov[1, 1] == 0:
        return None
    return float(cov[0, 1] / cov[1, 1])

def period_return(prices, days):
    if len(prices) < days + 1:
        return None
    return float(prices[-1] / prices[-days - 1] - 1)

def ytd_return_from_arr(prices, dates):
    year = dates[-1].year
    idx  = next((i for i, d in enumerate(dates) if d.year == year), None)
    if idx is None or idx >= len(prices) - 1:
        return None
    return float(prices[-1] / prices[idx] - 1)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    days   = trading_days(504)          # ~2 years
    prices = simulate_prices(504)

    returns = {t: pct_change(prices[t]) for t in ORDER}
    spy_ret = returns["SPY"]
    qqq_ret = returns["QQQ"]

    stats = {}
    chart_series = {}

    for ticker in TICKERS:
        p = prices[ticker]
        r = returns[ticker]

        # align length (returns is 1 shorter than prices)
        assert len(r) == len(spy_ret)

        # compute beta against SPY and QQQ
        b_spy = beta_calc(r, spy_ret)
        b_qqq = beta_calc(r, qqq_ret) if ticker != "QQQ" else 1.0

        # current / prev
        cur_price  = p[-1]
        prev_close = p[-2]
        day_chg    = (cur_price / prev_close - 1)

        # 52-week window (252 trading days)
        p_52 = p[-252:] if len(p) >= 252 else p
        high_52 = float(np.max(p_52))
        low_52  = float(np.min(p_52))

        r_1y = r[-252:] if len(r) >= 252 else r

        stats[ticker] = {
            "current_price":  safe(cur_price),
            "prev_close":     safe(prev_close),
            "day_change_pct": safe(day_chg),
            "52w_high":       safe(high_52),
            "52w_low":        safe(low_52),
            "avg_volume":     None,  # not simulated
            "ann_return_1y":  safe(annualized_return(r_1y)),
            "return_ytd":     safe(ytd_return_from_arr(p, days)),
            "return_1m":      safe(period_return(p, 21)),
            "return_3m":      safe(period_return(p, 63)),
            "return_6m":      safe(period_return(p, 126)),
            "ann_volatility": safe(annualized_vol(r)),
            "sharpe_ratio":   safe(sharpe(r)),
            "max_drawdown":   safe(max_drawdown(p)),
            "beta_vs_spy":    safe(b_spy),
            "beta_vs_qqq":    safe(b_qqq),
        }

        # Normalized price chart (last 252 days → base 100)
        p_chart = p[-252:]
        d_chart = days[-252:]
        norm    = (p_chart / p_chart[0]) * 100
        chart_series[ticker] = {
            "dates":  [str(d) for d in d_chart],
            "values": [safe(v) for v in norm],
        }

    # ── Correlation matrix ────────────────────────────────────────────────────
    ret_df = pd.DataFrame({t: returns[t] for t in TICKERS})
    corr_m = ret_df.corr()
    corr_data = {
        "tickers": TICKERS,
        "matrix":  [
            [safe(corr_m.loc[r, c]) for c in TICKERS]
            for r in TICKERS
        ],
    }

    # ── Rolling 30-day correlation vs QQQ ────────────────────────────────────
    rolling_corr = {}
    for ticker in TICKERS:
        if ticker == "QQQ":
            continue
        roll = ret_df[ticker].rolling(30).corr(ret_df["QQQ"]).dropna()
        roll_dates = [str(days[i + 1]) for i in roll.index]  # offset by 1 (diff)
        rolling_corr[ticker] = {
            "dates":  roll_dates,
            "values": [safe(v) for v in roll.values],
        }

    # ── Combined normalized chart ─────────────────────────────────────────────
    base_dates = chart_series[TICKERS[0]]["dates"]
    combined = {
        "dates":  base_dates,
        "series": {t: chart_series[t]["values"] for t in TICKERS},
    }

    # ── Candlestick-style volatility regimes (monthly) ───────────────────────
    # group into ~21-day blocks, compute rolling vol
    vol_regimes = {}
    for ticker in TICKERS:
        r = returns[ticker]
        monthly_vols = []
        monthly_labels = []
        for start in range(0, len(r) - 21, 21):
            block = r[start:start + 21]
            monthly_vols.append(safe(np.std(block, ddof=1) * np.sqrt(252)))
            monthly_labels.append(str(days[start]))
        vol_regimes[ticker] = {"dates": monthly_labels, "vols": monthly_vols}

    output = {
        "generated_at": "2026-05-09T20:00:00Z",
        "tickers":      TICKERS,
        "benchmark":    BENCHMARK,
        "note":         "Simulated data based on real ETF statistical properties",
        "stats":        stats,
        "correlation":  corr_data,
        "rolling_correlation_vs_qqq": rolling_corr,
        "price_chart":  combined,
        "vol_regimes":  vol_regimes,
    }

    os.makedirs("docs", exist_ok=True)
    with open("docs/data.json", "w") as f:
        json.dump(output, f, indent=2)
    print("✓ Saved docs/data.json")

    print("\n── Summary ─────────────────────────────────────────")
    print(f"{'Ticker':<8} {'Price':>8} {'1Y Ret':>8} {'Vol':>8} {'Sharpe':>7} {'Beta/SPY':>9} {'MaxDD':>8}")
    print("-" * 62)
    for t in TICKERS:
        s = stats[t]
        print(
            f"{t:<8} "
            f"{s['current_price']:>8.2f} "
            f"{s['ann_return_1y']:>7.1%} "
            f"{s['ann_volatility']:>7.1%} "
            f"{s['sharpe_ratio']:>7.2f} "
            f"{s['beta_vs_spy']:>9.2f} "
            f"{s['max_drawdown']:>7.1%}"
        )
    print()

if __name__ == "__main__":
    main()
