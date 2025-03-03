#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Run the Rebound Strategy backtest using the shared strategy runner
"""

import sys
from data_handler import download_spy_data
from strategies.rebound_strategy import ReboundStrategy
from strategy_runner import run_strategy_backtest, parse_common_args


def get_rebound_csv_fields():
    """Get the extra CSV fields specific to the Rebound strategy"""
    def get_purchase_price(strategy):
        return strategy.purchase_price if hasattr(strategy, 'purchase_price') else float('nan')
    
    def get_price_change_pct(strategy):
        if hasattr(strategy, 'purchase_price') and strategy.purchase_price and strategy.position:
            return (strategy.data.close[0] - strategy.purchase_price) / strategy.purchase_price * 100
        return float('nan')
    
    return [
        ('PurchasePrice', get_purchase_price),
        ('PriceChangePct', get_price_change_pct)
    ]


if __name__ == '__main__':
    # Parse command line arguments
    parser = parse_common_args()
    
    # Add strategy-specific arguments
    parser.add_argument('--drop', type=float, default=0.10, help='Drop threshold (e.g., 0.10 for 10%)')
    parser.add_argument('--rise', type=float, default=0.20, help='Rise threshold (e.g., 0.20 for 20%)')
    parser.add_argument('--lookback', type=int, default=5, help='Lookback period in days')
    
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
        'drop_threshold': args.drop,
        'rise_threshold': args.rise,
        'lookback_period': args.lookback
    }
    
    # Run the backtest
    success = run_strategy_backtest(
        strategy_class=ReboundStrategy,
        data_file=data_file,
        output_file=args.output,
        start_cash=args.cash,
        commission=args.commission,
        plot=not args.no_plot,
        strategy_params=strategy_params,
        csv_fields=get_rebound_csv_fields()
    )
    
    if success:
        print("Backtest completed successfully")
        sys.exit(0)
    else:
        print("Backtest failed")
        sys.exit(1) 