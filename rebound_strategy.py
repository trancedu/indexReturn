#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Rebound Strategy for SPY
This strategy buys when the price drops by 10% in a week (5 trading days)
and sells when the price rises by 20% from the purchase price.
"""

import backtrader as bt
import datetime
import os.path
import pandas as pd


class ReboundStrategy(bt.Strategy):
    """
    Rebound Strategy
    Buy when price drops by 10% in a week (5 trading days)
    Sell when price rises by 20% from purchase price
    Uses all available cash for buying and sells all shares when selling
    """
    params = (
        ('drop_threshold', 0.10),  # 10% drop threshold
        ('rise_threshold', 0.20),  # 20% rise threshold
        ('lookback_period', 5),    # 5 trading days (1 week)
    )
    
    def __init__(self):
        # Keep track of the purchase price
        self.purchase_price = None
        
        # To keep track of pending orders
        self.order = None
        
        # Set the sizer to use all available cash (100%)
        self.sizer = bt.sizers.PercentSizer(percents=100)
        
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
                self.log(f'BUY EXECUTED, {order.executed.price:.2f}, Size: {order.executed.size}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                # Record the purchase price
                self.purchase_price = order.executed.price
            elif order.issell():
                self.log(f'SELL EXECUTED, {order.executed.price:.2f}, Size: {order.executed.size}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                # Reset the purchase price
                self.purchase_price = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Reset orders
        self.order = None

    def next(self):
        # Check if an order is pending
        if self.order:
            return
            
        # Current closing price
        current_price = self.data.close[0]
        
        # Check if we are in the market
        if not self.position:
            # Not in the market, look for buy signal
            
            # Check if we have enough data for lookback
            if len(self.data) > self.params.lookback_period:
                # Price from lookback_period days ago
                past_price = self.data.close[-self.params.lookback_period]
                
                # Calculate the price drop percentage
                price_drop = (past_price - current_price) / past_price
                
                # If price has dropped by threshold or more, buy
                if price_drop >= self.params.drop_threshold:
                    cash = self.broker.getcash()
                    size = int(cash / current_price) # Calculate how many shares we can buy
                    value = size * current_price
                    
                    self.log(f'BUY CREATE, {current_price:.2f} (Price dropped by {price_drop:.2%} from {past_price:.2f})')
                    self.log(f'Using {value:.2f} of {cash:.2f} available cash to buy {size} shares')
                    
                    # Keep track of the created order to avoid a 2nd order
                    self.order = self.buy(size=size)
        else:
            # Already in the market, look for sell signal
            
            # Calculate the price rise percentage from purchase
            if self.purchase_price:
                price_rise = (current_price - self.purchase_price) / self.purchase_price
                
                # If price has risen by threshold or more, sell
                if price_rise >= self.params.rise_threshold:
                    size = self.position.size
                    value = size * current_price
                    
                    self.log(f'SELL CREATE, {current_price:.2f} (Price rose by {price_rise:.2%} from {self.purchase_price:.2f})')
                    self.log(f'Selling all {size} shares for approximately {value:.2f}')
                    
                    # Use close() to sell all shares
                    self.order = self.close()


def run_backtest(data_file, start_cash=10000.0, commission=0.001, 
                drop_threshold=0.10, rise_threshold=0.20, lookback_period=5):
    """Run the backtest with the given parameters"""
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add the Rebound Strategy
    cerebro.addstrategy(ReboundStrategy, 
                       drop_threshold=drop_threshold,
                       rise_threshold=rise_threshold,
                       lookback_period=lookback_period)
    
    # Set the default sizer to use 100% of available cash
    cerebro.addsizer(bt.sizers.PercentSizer, percents=100)

    # Load the data
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
    
    return True


if __name__ == '__main__':
    import argparse
    import sys
    from data_handler import download_spy_data, check_and_fix_csv
    
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
        
    # Check if the data file exists
    if not os.path.exists(data_file):
        print(f"Error: Data file {data_file} does not exist")
        sys.exit(1)
    
    # Check and fix CSV file format if needed
    if not check_and_fix_csv(data_file):
        print(f"Error: Could not validate or fix data file {data_file}")
        sys.exit(1)
    
    # Run the backtest
    success = run_backtest(
        data_file=data_file,
        start_cash=args.cash,
        commission=args.commission,
        drop_threshold=args.drop,
        rise_threshold=args.rise,
        lookback_period=args.lookback
    )
    
    if success:
        print("Backtest completed successfully")
        sys.exit(0)
    else:
        print("Backtest failed")
        sys.exit(1) 