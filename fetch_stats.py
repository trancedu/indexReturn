#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "yfinance>=0.2.54",
#   "pandas>=2.0.0",
#   "numpy>=1.24.0",
#   "scipy>=1.10.0",
# ]
# ///
"""
Fetches latest data for SOXX, QQQ, SOXL, TQQQ and computes
correlation, beta, and risk statistics. Outputs docs/data.json.
"""

import json
import math
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

TICKERS = ["SOXX", "QQQ", "SOXL", "TQQQ"]
BENCHMARK = "SPY"
ALL_TICKERS = TICKERS + [BENCHMARK]
RISK_FREE_RATE = 0.05  # annual

def safe(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return round(float(v), 6)

def download(tickers, period="2y"):
    raw = yf.download(tickers, period=period, auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:
        close = raw[["Close"]] if "Close" in raw.columns else raw
    close = close.dropna(how="all")
    return close

def pct_change_returns(prices):
    return prices.pct_change().dropna()

def annualized_return(returns, periods=252):
    total = (1 + returns).prod()
    n = len(returns)
    return float(total ** (periods / n) - 1)

def annualized_vol(returns, periods=252):
    return float(returns.std() * np.sqrt(periods))

def sharpe(returns, periods=252, rf=RISK_FREE_RATE):
    ann_ret = annualized_return(returns, periods)
    ann_vol = annualized_vol(returns, periods)
    if ann_vol == 0:
        return None
    return (ann_ret - rf) / ann_vol

def max_drawdown(prices):
    roll_max = prices.expanding().max()
    drawdown = (prices - roll_max) / roll_max
    return float(drawdown.min())

def beta(returns_asset, returns_bench):
    cov = np.cov(returns_asset, returns_bench)
    if cov[1, 1] == 0:
        return None
    return float(cov[0, 1] / cov[1, 1])

def period_return(prices, days):
    if len(prices) < days + 1:
        return None
    return float((prices.iloc[-1] / prices.iloc[-days - 1]) - 1)

def ytd_return(prices):
    today = prices.index[-1]
    start_of_year = pd.Timestamp(today.year, 1, 1)
    mask = prices.index >= start_of_year
    if mask.sum() < 2:
        return None
    ytd = prices[mask]
    return float((ytd.iloc[-1] / ytd.iloc[0]) - 1)

def price_series_for_chart(prices, n=252):
    """Return last n days normalized to 100 at start."""
    subset = prices.iloc[-n:] if len(prices) > n else prices
    normalized = (subset / subset.iloc[0]) * 100
    dates = [str(d.date()) for d in normalized.index]
    values = [safe(v) for v in normalized.values]
    return {"dates": dates, "values": values}

def main():
    print("Downloading price data…")
    prices = download(ALL_TICKERS)
    # Fill tickers that may be missing
    for t in ALL_TICKERS:
        if t not in prices.columns:
            print(f"WARNING: {t} not found in download")

    returns = pct_change_returns(prices)

    bench_ret = returns[BENCHMARK]
    bench_prices = prices[BENCHMARK]

    stats = {}
    chart_series = {}

    for ticker in TICKERS:
        if ticker not in prices.columns:
            continue
        p = prices[ticker].dropna()
        r = returns[ticker].dropna()

        # Align with benchmark
        aligned = pd.concat([r, bench_ret], axis=1).dropna()
        r_aligned = aligned.iloc[:, 0]
        b_aligned = aligned.iloc[:, 1]

        # Compute beta vs QQQ as well (if not QQQ itself)
        qqq_ret = returns["QQQ"].dropna() if "QQQ" in returns.columns else None

        info = {}
        try:
            yf_info = yf.Ticker(ticker).fast_info
            info["current_price"] = safe(yf_info.last_price)
            info["prev_close"] = safe(yf_info.previous_close)
            info["day_change_pct"] = safe(
                (yf_info.last_price / yf_info.previous_close - 1)
                if yf_info.previous_close else None
            )
            info["52w_high"] = safe(yf_info.year_high)
            info["52w_low"] = safe(yf_info.year_low)
            info["avg_volume"] = safe(yf_info.three_month_average_volume)
        except Exception:
            info["current_price"] = safe(p.iloc[-1]) if len(p) else None
            info["prev_close"] = safe(p.iloc[-2]) if len(p) > 1 else None
            info["day_change_pct"] = safe(
                (p.iloc[-1] / p.iloc[-2] - 1) if len(p) > 1 else None
            )
            info["52w_high"] = safe(p.rolling(252).max().iloc[-1]) if len(p) >= 252 else safe(p.max())
            info["52w_low"] = safe(p.rolling(252).min().iloc[-1]) if len(p) >= 252 else safe(p.min())
            info["avg_volume"] = None

        stats[ticker] = {
            **info,
            "ann_return_1y": safe(annualized_return(r.iloc[-252:]) if len(r) >= 252 else annualized_return(r)),
            "return_ytd": safe(ytd_return(p)),
            "return_1m": safe(period_return(p, 21)),
            "return_3m": safe(period_return(p, 63)),
            "return_6m": safe(period_return(p, 126)),
            "ann_volatility": safe(annualized_vol(r)),
            "sharpe_ratio": safe(sharpe(r)),
            "max_drawdown": safe(max_drawdown(p)),
            "beta_vs_spy": safe(beta(r_aligned.values, b_aligned.values)),
            "beta_vs_qqq": safe(
                beta(
                    *[v for v in pd.concat([r, qqq_ret], axis=1).dropna().values.T]
                ) if qqq_ret is not None and ticker != "QQQ" else 1.0
            ),
        }

        chart_series[ticker] = price_series_for_chart(p)

    # Correlation matrix of daily returns
    ret_df = returns[TICKERS].dropna()
    corr = ret_df.corr()
    corr_data = {
        "tickers": TICKERS,
        "matrix": [[safe(corr.loc[r, c]) for c in TICKERS] for r in TICKERS],
    }

    # Rolling 30-day correlation vs QQQ
    rolling_corr = {}
    if "QQQ" in ret_df.columns:
        for ticker in TICKERS:
            if ticker == "QQQ":
                continue
            roll = ret_df[ticker].rolling(30).corr(ret_df["QQQ"]).dropna()
            rolling_corr[ticker] = {
                "dates": [str(d.date()) for d in roll.index],
                "values": [safe(v) for v in roll.values],
            }

    # Combined normalized chart (all tickers, 1 year)
    combined_dates = chart_series[TICKERS[0]]["dates"] if TICKERS[0] in chart_series else []
    combined = {
        "dates": combined_dates,
        "series": {t: chart_series[t]["values"] for t in TICKERS if t in chart_series},
    }

    output = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "tickers": TICKERS,
        "benchmark": BENCHMARK,
        "stats": stats,
        "correlation": corr_data,
        "rolling_correlation_vs_qqq": rolling_corr,
        "price_chart": combined,
    }

    os.makedirs("docs", exist_ok=True)
    with open("docs/data.json", "w") as f:
        json.dump(output, f, indent=2)

    print("Saved docs/data.json")
    print("\nQuick Summary:")
    for t, s in stats.items():
        print(
            f"  {t}: price={s['current_price']}, "
            f"1Y={s['ann_return_1y']:.1%}, "
            f"vol={s['ann_volatility']:.1%}, "
            f"sharpe={s['sharpe_ratio']:.2f}, "
            f"beta_spy={s['beta_vs_spy']:.2f}"
        )

if __name__ == "__main__":
    main()
