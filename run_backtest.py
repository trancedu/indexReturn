#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Run the SMA Crossover Strategy backtest and save results to CSV
"""

import datetime
import os.path
import pandas as pd
import argparse
import sys

import backtrader as bt
from sma_crossover_strategy import SmaCrossStrategy, download_spy_data


def check_and_fix_csv(csv_file):
    """Check if the CSV file has the correct format and fix it if needed"""
    if not os.path.exists(csv_file):
        print(f"Error: CSV file {csv_file} does not exist")
        return False
    
    try:
        # Try to read the file with pandas
        df = pd.read_csv(csv_file)
        
        print(f"CSV file structure:")
        print(df.head(2))
        
        # Check for required columns
        required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"Error: Missing required columns: {missing_cols}")
            return False
            
        # Add OpenInterest if missing
        if 'OpenInterest' not in df.columns:
            df['OpenInterest'] = 0
            df.to_csv(csv_file, index=False)
            print("Added OpenInterest column")
        
        return True
        
    except Exception as e:
        print(f"Error checking CSV file: {e}")
        return False


class CSVWriter(bt.Analyzer):
    """Analyzer to save trade data to CSV"""
    
    params = (
        ('filename', 'backtest_results.csv'),
    )
    
    def start(self):
        self.results = []
        
    def next(self):
        # Get current portfolio value
        portfolio_value = self.strategy.broker.getvalue()
        
        # Get current position
        position = self.strategy.position.size if self.strategy.position else 0
        
        # Get current price
        price = self.datas[0].close[0]
        
        # Get current date
        date = self.datas[0].datetime.date(0)
        
        # Get signal (if any)
        signal = 0
        if hasattr(self.strategy, 'order') and self.strategy.order is not None:
            if self.strategy.order.isbuy():
                signal = 1
            elif self.strategy.order.issell():
                signal = -1
        
        # Store data
        self.results.append({
            'date': date,
            'close': price,
            'portfolio_value': portfolio_value,
            'position': position,
            'signal': signal
        })
    
    def stop(self):
        # Convert results to DataFrame and save to CSV
        df = pd.DataFrame(self.results)
        # Convert date objects to strings in the format expected by visualize_results.py
        df['date'] = df['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
        df.to_csv(self.p.filename, index=False)
        print(f"Results saved to {self.p.filename}")


def run_backtest(data_file, output_file='backtest_results.csv', start_cash=10000.0, commission=0.001,
                fast_period=50, slow_period=200, plot=True):
    """
    Run the SMA Crossover Strategy backtest and save results to CSV
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
        
        # Add the SMA Crossover Strategy
        cerebro.addstrategy(SmaCrossStrategy, 
                           fast_period=fast_period, 
                           slow_period=slow_period)
        
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
        print(f"Sharpe Ratio: {strategy.analyzers.sharpe.get_analysis()['sharperatio']:.3f}")
        print(f"Max Drawdown: {strategy.analyzers.drawdown.get_analysis()['max']['drawdown']:.2f}%")
        print(f"Total Return: {strategy.analyzers.returns.get_analysis()['rtot']:.2f}%")
        
        # Plot the result if requested
        if plot:
            cerebro.plot(style='candlestick', barup='green', bardown='red')
        
        print(f"Backtest results saved to {output_file}")
        return True
        
    except Exception as e:
        print(f"Error running backtest: {e}")
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run SMA Crossover Strategy Backtest')
    parser.add_argument('--data', type=str, default='spy_data.csv', help='Data file to use')
    parser.add_argument('--output', type=str, default='backtest_results.csv', help='Output file for results')
    parser.add_argument('--cash', type=float, default=10000.0, help='Starting cash')
    parser.add_argument('--commission', type=float, default=0.001, help='Commission rate')
    parser.add_argument('--fast', type=int, default=50, help='Fast SMA period')
    parser.add_argument('--slow', type=int, default=200, help='Slow SMA period')
    parser.add_argument('--no-plot', action='store_true', help='Disable plotting')
    parser.add_argument('--download', action='store_true', help='Download fresh data')
    parser.add_argument('--start-date', type=str, default='1993-01-01', help='Start date for data download')
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
        fast_period=args.fast,
        slow_period=args.slow,
        plot=not args.no_plot
    )
    
    if success:
        print("Backtest completed successfully")
        sys.exit(0)
    else:
        print("Backtest failed")
        sys.exit(1) 