#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Run the Market Momentum Strategy backtest using the shared strategy runner
"""

import sys
import os

# Add parent directory to path to allow relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_handler import download_spy_data
from strategies.market_momentum_strategy import MarketMomentumStrategy
from strategy_runner import run_strategy_backtest, parse_common_args


if __name__ == '__main__':
    # Parse command line arguments
    parser = parse_common_args()
    
    # Add strategy-specific arguments
    parser.add_argument('--fast-ma', type=int, default=10, help='Fast moving average period')
    parser.add_argument('--medium-ma', type=int, default=20, help='Medium moving average period')
    parser.add_argument('--rsi-period', type=int, default=14, help='RSI period')
    parser.add_argument('--rsi-oversold', type=int, default=30, help='RSI oversold threshold')
    parser.add_argument('--rsi-overbought', type=int, default=70, help='RSI overbought threshold')
    parser.add_argument('--trail-percent', type=float, default=0.05, help='Trailing stop percentage')
    parser.add_argument('--risk-per-trade', type=float, default=0.02, help='Risk per trade as fraction of portfolio')
    
    args = parser.parse_args()
    
    # Download data if requested
    if args.download:
        print(f"Downloading fresh data from {args.start_date} to {args.end_date}...")
        data_file = download_spy_data(args.start_date, args.end_date, args.data)
        if not data_file:
            print("Error: Failed to download data")
            sys.exit(1)
    else:
        data_file = args.data
    
    # Set up strategy parameters
    strategy_params = {
        'fast_ma': args.fast_ma,
        'medium_ma': args.medium_ma,
        'rsi_period': args.rsi_period,
        'rsi_oversold': args.rsi_oversold,
        'rsi_overbought': args.rsi_overbought,
        'trail_percent': args.trail_percent,
        'risk_per_trade': args.risk_per_trade
    }
    
    # Run the backtest
    success = run_strategy_backtest(
        strategy_class=MarketMomentumStrategy,
        data_file=data_file,
        output_file=args.output,
        start_cash=args.cash,
        commission=args.commission,
        plot=not args.no_plot,
        strategy_params=strategy_params
    )
    
    if success:
        print("Backtest completed successfully")
        sys.exit(0)
    else:
        print("Backtest failed")
        sys.exit(1) 