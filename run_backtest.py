#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Run the SMA Crossover Strategy backtest and save results to CSV
"""

import datetime
import os.path
import pandas as pd
import argparse

import backtrader as bt
from sma_crossover_strategy import SmaCrossStrategy, download_spy_data


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
    """Run the backtest with the given parameters and save results to CSV"""
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(SmaCrossStrategy, 
                        fast_period=fast_period, 
                        slow_period=slow_period)

    # Load the data
    data = bt.feeds.YahooFinanceCSVData(
        dataname=data_file,
        # Do not pass values before this date
        fromdate=datetime.datetime(1993, 1, 1),
        # Do not pass values after this date
        todate=datetime.datetime(2023, 12, 31),
        reverse=False,
        # CSV format specifications
        dtformat='%Y-%m-%d',
        datetime=0,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,
        openinterest=-1,
        # Skip the header row
        headers=True
    )

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(start_cash)

    # Set the commission
    cerebro.broker.setcommission(commission=commission)

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(CSVWriter, _name='csvwriter', filename=output_file)

    # Print out the starting conditions
    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')

    # Run the backtest
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run SMA Crossover Strategy Backtest')
    parser.add_argument('--data', type=str, default='spy_data.csv',
                        help='Path to the data CSV file')
    parser.add_argument('--output', type=str, default='backtest_results.csv',
                        help='Path to save the results CSV file')
    parser.add_argument('--cash', type=float, default=10000.0,
                        help='Initial cash amount')
    parser.add_argument('--commission', type=float, default=0.001,
                        help='Commission rate')
    parser.add_argument('--fast', type=int, default=50,
                        help='Fast SMA period')
    parser.add_argument('--slow', type=int, default=200,
                        help='Slow SMA period')
    parser.add_argument('--no-plot', action='store_true',
                        help='Disable plotting')
    parser.add_argument('--force-download', action='store_true',
                        help='Force re-download of data even if file exists')
    args = parser.parse_args()
    
    # Define date range (30 years)
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=365 * 30)
    
    # Download data or use existing file
    data_file = args.data
    if not os.path.exists(data_file) or args.force_download:
        data_file = download_spy_data(start_date, end_date, data_file)
    
    # Run the backtest
    run_backtest(
        data_file=data_file,
        output_file=args.output,
        start_cash=args.cash,
        commission=args.commission,
        fast_period=args.fast,
        slow_period=args.slow,
        plot=not args.no_plot
    ) 