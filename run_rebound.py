#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Run the Rebound Strategy backtest and save results to CSV
"""

import datetime
import os.path
import pandas as pd
import argparse
import sys

import backtrader as bt
from rebound_strategy import ReboundStrategy
from data_handler import download_spy_data, check_and_fix_csv


class CSVWriter(bt.Analyzer):
    """Analyzer to save trade data to CSV"""
    
    params = (
        ('filename', 'rebound_results.csv'),
    )
    
    def start(self):
        self.results = []
        
    def next(self):
        # Get current portfolio value
        portfolio_value = self.strategy.broker.getvalue()
        
        # Get current position
        position = self.strategy.position.size if self.strategy.position else 0
        
        # Get current date
        date = self.strategy.datas[0].datetime.date(0)
        
        # Get current prices
        close = self.strategy.datas[0].close[0]
        
        # Get purchase price if available
        purchase_price = self.strategy.purchase_price if hasattr(self.strategy, 'purchase_price') else None
        
        # Calculate price change from purchase if applicable
        price_change_pct = None
        if purchase_price and position > 0:
            price_change_pct = (close - purchase_price) / purchase_price * 100
        
        # Get cash
        cash = self.strategy.broker.getcash()
        
        # Store the results
        self.results.append({
            'Date': date.isoformat(),
            'Close': close,
            'Position': position,
            'PurchasePrice': purchase_price if purchase_price is not None else float('nan'),
            'PriceChangePct': price_change_pct if price_change_pct is not None else float('nan'),
            'Cash': cash,
            'PortfolioValue': portfolio_value
        })
    
    def stop(self):
        # Convert results to DataFrame and save to CSV
        results_df = pd.DataFrame(self.results)
        results_df.to_csv(self.p.filename, index=False)
        print(f"Results saved to {self.p.filename}")


def run_backtest(data_file, output_file='rebound_results.csv', start_cash=10000.0, commission=0.001,
                drop_threshold=0.10, rise_threshold=0.20, lookback_period=5, plot=True):
    """
    Run the Rebound Strategy backtest and save results to CSV
    """
    # Check if the data file exists
    if not os.path.exists(data_file):
        print(f"Error: Data file {data_file} does not exist")
        return False
    
    # Check and fix CSV file format if needed
    if not check_and_fix_csv(data_file):
        print(f"Error: Could not validate or fix data file {data_file}")
        return False
    
    try:
        # Create a Backtrader cerebro instance
        cerebro = bt.Cerebro()
        
        # Add the Rebound Strategy
        cerebro.addstrategy(ReboundStrategy, 
                           drop_threshold=drop_threshold,
                           rise_threshold=rise_threshold,
                           lookback_period=lookback_period)
        
        # Set the default sizer to use 100% of available cash
        cerebro.addsizer(bt.sizers.PercentSizer, percents=100)
        
        # Load the data
        print(f"Loading data from {data_file}...")
        data = bt.feeds.GenericCSVData(
            dataname=data_file,
            dtformat='%Y-%m-%d',
            datetime=0,
            open=1,
            high=2,
            low=3,
            close=4,
            volume=5,
            openinterest=6
        )
        cerebro.adddata(data)
        
        # Set the cash
        cerebro.broker.setcash(start_cash)
        
        # Set the commission
        cerebro.broker.setcommission(commission=commission)
        
        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(CSVWriter, _name='csvwriter', filename=output_file)
        
        # Print starting conditions
        print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')
        
        # Run the backtest
        print("Running backtest...")
        results = cerebro.run()
        
        # Print out the final result
        print(f'Final Portfolio Value: {cerebro.broker.getvalue():.2f}')
        
        # Print analyzer results
        strategy = results[0]
        sharpe_ratio = strategy.analyzers.sharpe.get_analysis().get('sharperatio', 0.0)
        max_drawdown = strategy.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0.0)
        total_return = strategy.analyzers.returns.get_analysis().get('rtot', 0.0)
        
        print(f"Sharpe Ratio: {sharpe_ratio:.3f}")
        print(f"Max Drawdown: {max_drawdown:.2f}%")
        print(f"Total Return: {total_return:.2f}%")
        
        # Plot the result if requested
        if plot:
            cerebro.plot(style='candlestick', barup='green', bardown='red')
        
        print(f"Backtest results saved to {output_file}")
        return True
        
    except Exception as e:
        print(f"Error running backtest: {e}")
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Rebound Strategy Backtest')
    parser.add_argument('--data', type=str, default='spy_data.csv', help='Data file to use')
    parser.add_argument('--output', type=str, default='rebound_results.csv', help='Output file for results')
    parser.add_argument('--cash', type=float, default=10000.0, help='Starting cash')
    parser.add_argument('--commission', type=float, default=0.001, help='Commission rate')
    parser.add_argument('--drop', type=float, default=0.10, help='Drop threshold (e.g., 0.10 for 10%)')
    parser.add_argument('--rise', type=float, default=0.20, help='Rise threshold (e.g., 0.20 for 20%)')
    parser.add_argument('--lookback', type=int, default=5, help='Lookback period in days')
    parser.add_argument('--no-plot', action='store_true', help='Disable plotting')
    parser.add_argument('--download', action='store_true', help='Download fresh data')
    parser.add_argument('--start-date', type=str, default='2000-01-01', help='Start date for data download')
    parser.add_argument('--end-date', type=str, default='2023-12-31', help='End date for data download')
    
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
    success = run_backtest(
        data_file=data_file,
        output_file=args.output,
        start_cash=args.cash,
        commission=args.commission,
        drop_threshold=args.drop,
        rise_threshold=args.rise,
        lookback_period=args.lookback,
        plot=not args.no_plot
    )
    
    if success:
        print("Backtest completed successfully")
        sys.exit(0)
    else:
        print("Backtest failed")
        sys.exit(1) 