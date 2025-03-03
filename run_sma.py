#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Run the SMA Crossover Strategy backtest using the shared strategy runner
"""

import sys
from data_handler import download_spy_data
from sma_crossover_strategy import SmaCrossStrategy
from strategy_runner import run_strategy_backtest, parse_common_args


def get_sma_csv_fields():
    """Get the extra CSV fields specific to the SMA Crossover strategy"""
    def get_fast_sma(strategy):
        return strategy.fast_sma[0] if hasattr(strategy, 'fast_sma') else float('nan')
    
    def get_slow_sma(strategy):
        return strategy.slow_sma[0] if hasattr(strategy, 'slow_sma') else float('nan')
    
    return [
        ('FastSMA', get_fast_sma),
        ('SlowSMA', get_slow_sma)
    ]


if __name__ == '__main__':
    # Parse command line arguments
    parser = parse_common_args()
    
    # Add strategy-specific arguments
    parser.add_argument('--fast', type=int, default=50, help='Fast SMA period')
    parser.add_argument('--slow', type=int, default=200, help='Slow SMA period')
    
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
        'fast_period': args.fast,
        'slow_period': args.slow
    }
    
    # Run the backtest
    success = run_strategy_backtest(
        strategy_class=SmaCrossStrategy,
        data_file=data_file,
        output_file=args.output,
        start_cash=args.cash,
        commission=args.commission,
        plot=not args.no_plot,
        strategy_params=strategy_params,
        csv_fields=get_sma_csv_fields()
    )
    
    if success:
        print("Backtest completed successfully")
        sys.exit(0)
    else:
        print("Backtest failed")
        sys.exit(1) 