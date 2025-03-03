#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple Moving Average Crossover Strategy for SPY
This strategy buys when the fast SMA crosses above the slow SMA
and sells when the fast SMA crosses below the slow SMA.
"""

import datetime
import os.path
import sys

import backtrader as bt
import backtrader.feeds as btfeeds
import pandas as pd
import yfinance as yf


class SmaCrossStrategy(bt.Strategy):
    """
    Simple Moving Average Crossover Strategy
    """
    params = (
        ('fast_period', 50),  # Fast moving average period
        ('slow_period', 200),  # Slow moving average period
    )

    def __init__(self):
        # Initialize moving averages
        self.fast_sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.fast_period)
        self.slow_sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.slow_period)
        
        # Create a CrossOver Signal
        self.crossover = bt.indicators.CrossOver(self.fast_sma, self.slow_sma)
        
        # To keep track of pending orders
        self.order = None
        
    def log(self, txt, dt=None):
        """Logging function for this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Order submitted/accepted - no action needed
            return

        # Check if an order has been completed
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, {order.executed.price:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED, {order.executed.price:.2f}')

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Reset orders
        self.order = None

    def next(self):
        # Check if an order is pending
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            # Not in the market, look for buy signal
            if self.crossover > 0:  # Fast SMA crosses above slow SMA
                self.log(f'BUY CREATE, {self.data.close[0]:.2f}')
                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy()
        else:
            # Already in the market, look for sell signal
            if self.crossover < 0:  # Fast SMA crosses below slow SMA
                self.log(f'SELL CREATE, {self.data.close[0]:.2f}')
                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()


def download_spy_data(start_date, end_date, filename='spy_data.csv'):
    """
    Download SPY data from Yahoo Finance and save to CSV
    """
    try:
        # Download SPY data
        print(f"Downloading SPY data from {start_date} to {end_date}...")
        spy_data = yf.download('SPY', start=start_date, end=end_date)
        
        if spy_data.empty:
            print("Error: No data downloaded from Yahoo Finance")
            return None
            
        print("Data downloaded successfully. Structure:")
        print(spy_data.head(2))
        
        # Handle multi-index columns if present
        if isinstance(spy_data.columns, pd.MultiIndex):
            print("Detected multi-index columns. Flattening structure...")
            spy_data.columns = spy_data.columns.get_level_values(0)
        
        # Reset the index to make Date a column
        spy_data = spy_data.reset_index()
        
        # Add OpenInterest column (required by Backtrader)
        spy_data['OpenInterest'] = 0
        
        # Save to CSV with proper format
        spy_data.to_csv(filename, index=False)
        print(f"Data saved to {filename}")
        
        return filename
        
    except Exception as e:
        print(f"Error downloading SPY data: {e}")
        return None


def run_backtest(data_file, start_cash=10000.0, commission=0.001):
    """Run the backtest with the given parameters"""
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(SmaCrossStrategy)

    # Load the data
    data = bt.feeds.YahooFinanceCSVData(
        dataname=data_file,
        # Do not pass values before this date
        fromdate=datetime.datetime(1993, 1, 1),
        # Do not pass values after this date
        todate=datetime.datetime(2023, 12, 31),
        reverse=False)

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
    
    # Plot the result
    cerebro.plot(style='candlestick', barup='green', bardown='red')


if __name__ == '__main__':
    # Define date range (30 years)
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=365 * 30)
    
    # Download data or use existing file
    data_file = 'spy_data.csv'
    if not os.path.exists(data_file):
        data_file = download_spy_data(start_date, end_date, data_file)
    
    # Run the backtest
    run_backtest(data_file) 