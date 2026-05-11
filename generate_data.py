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
Generates realistic price paths for SOXX, QQQ, SOXL, TQQQ via a
Brownian bridge: starts at known May-2024 prices, ends at realistic
May-2026 prices. This gives accurate 1Y/2Y return shapes and
realistic betas/correlations calibrated to real ETF properties.

Run:  uv run generate_data.py
Out:  docs/data.json
"""

import json, math, os
from datetime import date, timedelta
import numpy as np
import pandas as pd

RNG = np.random.default_rng(7)

TICKERS   = ["SOXX", "QQQ", "SOXL", "TQQQ"]
BENCHMARK = "SPY"
ORDER     = ["SPY", "QQQ", "SOXX", "SOXL", "TQQQ"]

# ── Anchor prices ─────────────────────────────────────────────────────────────
# Approximate prices ~2 years ago (May 2024) and today (May 2026).
# These bracket the Brownian bridge so total returns are realistic.
START_PRICES = {   # ≈ May 2024
    "SPY":  520.00,
    "QQQ":  438.00,
    "SOXX": 218.00,
    "SOXL":  50.00,
    "TQQQ":  62.00,
}
END_PRICES = {     # ≈ May 2026 reasonable projection
    "SPY":  593.00,   # +14 % over 2 yr  (~7 % / yr)
    "QQQ":  510.00,   # +16 % over 2 yr  (~8 % / yr)
    "SOXX": 237.00,   # +9 %  over 2 yr  (~4 % / yr)
    "SOXL":  42.00,   # -16 % over 2 yr  (leverage decay in choppy mkt)
    "TQQQ":  80.00,   # +29 % over 2 yr  (leveraged, some growth)
}

# ── Volatility (daily σ) calibrated from historical ETF data ──────────────────
DAILY_VOL = {
    "SPY":  0.0095,
    "QQQ":  0.0125,
    "SOXX": 0.0160,
    "SOXL": 0.0465,
    "TQQQ": 0.0370,
}

# ── Correlation structure (Cholesky) ─────────────────────────────────────────
# Order: SPY, QQQ, SOXX, SOXL, TQQQ
CORR = np.array([
    [1.000, 0.940, 0.860, 0.780, 0.890],
    [0.940, 1.000, 0.890, 0.820, 0.970],
    [0.860, 0.890, 1.000, 0.960, 0.840],
    [0.780, 0.820, 0.960, 1.000, 0.790],
    [0.890, 0.970, 0.840, 0.790, 1.000],
])

RISK_FREE = 0.05

# ── Helpers ───────────────────────────────────────────────────────────────────
def safe(v):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    return round(float(v), 6)

def trading_days(n=504):
    end = date(2026, 5, 9)
    days, d = [], end
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)
    return list(reversed(days))

def brownian_bridge(start, end, sigma, n):
    """
    Simulate a log-price Brownian bridge from log(start) to log(end)
    in n steps with per-step volatility sigma.
    Returns n+1 prices (index 0 = start, index n = end).
    """
    log_s, log_e = math.log(start), math.log(end)
    # Pure Brownian motion over n steps
    raw = np.cumsum(RNG.standard_normal(n)) * sigma
    raw = np.concatenate([[0], raw])
    # Bridge correction: subtract the linear drift needed to hit log_e
    t = np.linspace(0, 1, n + 1)
    bridge = log_s + (log_e - log_s) * t + (raw - raw[-1] * t)
    return np.exp(bridge)

def simulate_prices(n=504):
    L = np.linalg.cholesky(CORR)
    # Generate correlated noise for each ticker's bridge corrections
    Z = RNG.standard_normal((n, len(ORDER)))
    corr_Z = Z @ L.T  # shape (n, 5)
    prices = {}
    for i, ticker in enumerate(ORDER):
        sig = DAILY_VOL[ticker]
        log_s = math.log(START_PRICES[ticker])
        log_e = math.log(END_PRICES[ticker])
        raw = np.cumsum(corr_Z[:, i]) * sig
        raw = np.concatenate([[0.0], raw])
        t = np.linspace(0, 1, n + 1)
        bridge = log_s + (log_e - log_s) * t + (raw - raw[-1] * t)
        prices[ticker] = np.exp(bridge)
    return prices   # each array has n+1 values (days 0..n)

def pct_change(arr):
    return np.diff(arr) / arr[:-1]

def annualized_return(rets, periods=252):
    if len(rets) == 0:
        return None
    return float(np.prod(1 + rets) ** (periods / len(rets)) - 1)

def annualized_vol(rets, periods=252):
    return float(np.std(rets, ddof=1) * np.sqrt(periods))

def sharpe(rets, rf=RISK_FREE, periods=252):
    ar = annualized_return(rets, periods)
    av = annualized_vol(rets, periods)
    if ar is None or av == 0:
        return None
    return (ar - rf) / av

def max_drawdown(prices):
    peak = np.maximum.accumulate(prices)
    dd = (prices - peak) / peak
    return float(np.min(dd))

def beta_calc(asset, bench):
    cov = np.cov(asset, bench)
    return float(cov[0, 1] / cov[1, 1]) if cov[1, 1] != 0 else None

def period_return(prices, days):
    if len(prices) < days + 1:
        return None
    return float(prices[-1] / prices[-days - 1] - 1)

def ytd_return(prices, dates):
    year = dates[-1].year
    idx = next((i for i, d in enumerate(dates) if d.year == year), None)
    if idx is None or idx >= len(prices) - 1:
        return None
    return float(prices[-1] / prices[idx] - 1)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    n_days = 504  # ~2 years of trading days
    days   = trading_days(n_days + 1)[:n_days + 1]   # n+1 dates
    prices = simulate_prices(n_days)                  # each: n+1 values

    # Returns arrays (length n_days)
    returns = {t: pct_change(prices[t]) for t in ORDER}
    spy_ret = returns["SPY"]
    qqq_ret = returns["QQQ"]

    stats       = {}
    chart_series = {}

    for ticker in TICKERS:
        p = prices[ticker]   # n+1 prices
        r = returns[ticker]  # n_days returns

        cur_price  = p[-1]
        prev_close = p[-2]

        p_52 = p[-252:] if len(p) >= 252 else p
        h52  = float(np.max(p_52))
        l52  = float(np.min(p_52))

        r_1y = r[-252:] if len(r) >= 252 else r

        b_spy = beta_calc(r, spy_ret)
        b_qqq = beta_calc(r, qqq_ret) if ticker != "QQQ" else 1.0

        stats[ticker] = {
            "current_price":  safe(cur_price),
            "prev_close":     safe(prev_close),
            "day_change_pct": safe((cur_price / prev_close) - 1),
            "52w_high":       safe(h52),
            "52w_low":        safe(l52),
            "avg_volume":     None,
            "ann_return_1y":  safe(annualized_return(r_1y)),
            "return_ytd":     safe(ytd_return(p, days)),
            "return_1m":      safe(period_return(p, 21)),
            "return_3m":      safe(period_return(p, 63)),
            "return_6m":      safe(period_return(p, 126)),
            "ann_volatility": safe(annualized_vol(r)),
            "sharpe_ratio":   safe(sharpe(r)),
            "max_drawdown":   safe(max_drawdown(p)),
            "beta_vs_spy":    safe(b_spy),
            "beta_vs_qqq":    safe(b_qqq),
        }

        # Normalized price chart (last 252 days)
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
        "matrix": [[safe(corr_m.loc[r, c]) for c in TICKERS] for r in TICKERS],
    }

    # ── Rolling 30-day correlation vs QQQ ────────────────────────────────────
    rolling_corr = {}
    for ticker in TICKERS:
        if ticker == "QQQ":
            continue
        roll = ret_df[ticker].rolling(30).corr(ret_df["QQQ"]).dropna()
        roll_dates = [str(days[i + 1]) for i in roll.index]
        rolling_corr[ticker] = {
            "dates":  roll_dates,
            "values": [safe(v) for v in roll.values],
        }

    # ── Combined price chart ──────────────────────────────────────────────────
    combined = {
        "dates":  chart_series[TICKERS[0]]["dates"],
        "series": {t: chart_series[t]["values"] for t in TICKERS},
    }

    # ── Monthly realized volatility ───────────────────────────────────────────
    vol_regimes = {}
    for ticker in TICKERS:
        r = returns[ticker]
        vols, labels = [], []
        for start in range(0, len(r) - 21, 21):
            block = r[start:start + 21]
            vols.append(safe(np.std(block, ddof=1) * np.sqrt(252)))
            labels.append(str(days[start]))
        vol_regimes[ticker] = {"dates": labels, "vols": vols}

    output = {
        "generated_at": "2026-05-09T21:00:00Z",
        "tickers":      TICKERS,
        "benchmark":    BENCHMARK,
        "note":         "Simulated via Brownian bridge anchored to real ETF price levels",
        "stats":        stats,
        "correlation":  corr_data,
        "rolling_correlation_vs_qqq": rolling_corr,
        "price_chart":  combined,
        "vol_regimes":  vol_regimes,
    }

    os.makedirs("docs", exist_ok=True)
    with open("docs/data.json", "w") as f:
        json.dump(output, f, indent=2)
    print("✓ docs/data.json written")

    print(f"\n{'Ticker':<8} {'Start':>8} {'Now':>8} {'2Y Ret':>8} {'1Y Ret':>8} "
          f"{'Vol':>7} {'Sharpe':>7} {'Beta/SPY':>9} {'MaxDD':>8}")
    print("-" * 74)
    for t in TICKERS:
        s = stats[t]
        start = START_PRICES[t]
        two_y = (s['current_price'] / start) - 1
        print(f"{t:<8} ${start:>7.2f} ${s['current_price']:>7.2f} "
              f"{two_y:>7.1%} {s['ann_return_1y']:>7.1%} "
              f"{s['ann_volatility']:>6.1%} {s['sharpe_ratio']:>7.2f} "
              f"{s['beta_vs_spy']:>9.2f} {s['max_drawdown']:>7.1%}")

if __name__ == "__main__":
    main()
