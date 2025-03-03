#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Run the Buy and Hold Strategy backtest using the shared strategy runner
"""

import sys
from data_handler import download_spy_data
from buy_and_hold_strategy import BuyAndHoldStrategy
from strategy_runner import run_strategy_backtest, parse_common_args


if __name__ == '__main__':
    # Parse command line arguments
    parser = parse_common_args()
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
    
    # Run the backtest
    success = run_strategy_backtest(
        strategy_class=BuyAndHoldStrategy,
        data_file=data_file,
        output_file=args.output,
        start_cash=args.cash,
        commission=args.commission,
        plot=not args.no_plot
    )
    
    if success:
        print("Backtest completed successfully")
        sys.exit(0)
    else:
        print("Backtest failed")
        sys.exit(1) 