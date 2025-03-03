#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Market Momentum Strategy for SPY
This strategy is designed to be more aggressive and stay in the market more often.
It uses multiple entry signals and trailing stops to capture more opportunities.
"""

import backtrader as bt
import datetime
import os.path
import pandas as pd


class MarketMomentumStrategy(bt.Strategy):
    """
    Market Momentum Strategy
    - Uses RSI for overbought/oversold conditions
    - Uses short-term moving averages for trend direction
    - Implements trailing stops for exits
    - Scales in during pullbacks in uptrends
    """
    params = (
        ('fast_ma', 10),          # Fast moving average period (10 days)
        ('medium_ma', 30),        # Medium moving average period (30 days)
        ('rsi_period', 14),       # RSI period
        ('rsi_oversold', 40),     # RSI oversold threshold (more aggressive than typical 30)
        ('rsi_overbought', 70),   # RSI overbought threshold
        ('trail_percent', 0.07),  # Trailing stop percentage (7%)
        ('risk_per_trade', 0.5),  # Risk 50% of available cash per entry signal
    )
    
    def __init__(self):
        # Initialize indicators
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.fast_ma)
        self.medium_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.medium_ma)
        
        # RSI indicator
        self.rsi = bt.indicators.RelativeStrengthIndex(
            period=self.params.rsi_period)
        
        # MACD for trend strength
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=12,
            period_me2=26,
            period_signal=9)
        
        # ATR for volatility measurement
        self.atr = bt.indicators.ATR(period=14)
        
        # To keep track of pending orders
        self.order = None
        
        # To keep track of trailing stop orders
        self.trailing_stop = None
        
        # Set the sizer to use percentage of available cash
        self.sizer = bt.sizers.PercentSizer(percents=self.params.risk_per_trade * 100)
        
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
                # Set trailing stop if not already set
                if not self.trailing_stop:
                    stop_price = order.executed.price * (1.0 - self.params.trail_percent)
                    self.trailing_stop = order.executed.price
                    self.log(f'TRAILING STOP SET AT {stop_price:.2f} ({self.params.trail_percent:.1%} below entry)')
            elif order.issell():
                self.log(f'SELL EXECUTED, {order.executed.price:.2f}, Size: {order.executed.size}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                # Reset trailing stop if position is closed
                if not self.position:
                    self.trailing_stop = None

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
        
        # Update trailing stop if we have a position
        if self.position and self.trailing_stop:
            # If price has moved up, move the trailing stop up
            if current_price > self.trailing_stop * (1.0 + self.params.trail_percent):
                new_stop = current_price * (1.0 - self.params.trail_percent)
                self.trailing_stop = current_price
                self.log(f'TRAILING STOP UPDATED TO {new_stop:.2f}')
            
            # Check if price has hit the trailing stop
            if current_price < self.trailing_stop * (1.0 - self.params.trail_percent):
                self.log(f'TRAILING STOP HIT, SELLING AT {current_price:.2f}')
                # Calculate position size to sell (all shares)
                size = self.position.size
                value = size * current_price
                self.log(f'Selling all {size} shares for approximately {value:.2f}')
                self.order = self.close()
                return
        
        # Entry signals
        if not self.position or self.position.size < 3 * int(self.broker.getcash() / current_price * self.params.risk_per_trade):
            # Signal 1: Fast MA crosses above Medium MA (uptrend)
            uptrend = self.fast_ma[0] > self.medium_ma[0] and self.fast_ma[-1] <= self.medium_ma[-1]
            
            # Signal 2: RSI crosses above oversold level (momentum shift)
            rsi_signal = self.rsi[0] > self.params.rsi_oversold and self.rsi[-1] <= self.params.rsi_oversold
            
            # Signal 3: MACD histogram turns positive (momentum confirmation)
            macd_signal = self.macd.macd[0] > self.macd.signal[0] and self.macd.macd[-1] <= self.macd.signal[-1]
            
            # Signal 4: Price pullback in uptrend (buying dips)
            pullback = (self.fast_ma[0] > self.medium_ma[0] and 
                       current_price < self.fast_ma[0] and 
                       current_price > self.data.close[-1])
            
            # If any of the signals are triggered, enter the market
            if uptrend or rsi_signal or macd_signal or pullback:
                # Calculate position size based on available cash and risk parameter
                cash = self.broker.getcash()
                risk_amount = cash * self.params.risk_per_trade
                size = int(risk_amount / current_price)
                
                if size > 0:
                    signal_type = []
                    if uptrend: signal_type.append("Uptrend")
                    if rsi_signal: signal_type.append("RSI Oversold")
                    if macd_signal: signal_type.append("MACD Signal")
                    if pullback: signal_type.append("Pullback")
                    
                    signal_str = ", ".join(signal_type)
                    self.log(f'BUY SIGNAL: {signal_str}')
                    self.log(f'BUY CREATE, {current_price:.2f}, RSI: {self.rsi[0]:.1f}')
                    self.log(f'Using {size * current_price:.2f} of {cash:.2f} available cash to buy {size} shares')
                    
                    # Keep track of the created order to avoid a 2nd order
                    self.order = self.buy(size=size)
        
        # Exit signals (in addition to trailing stop)
        elif self.position:
            # Signal 1: RSI overbought
            rsi_exit = self.rsi[0] > self.params.rsi_overbought
            
            # Signal 2: Fast MA crosses below Medium MA (downtrend)
            downtrend = self.fast_ma[0] < self.medium_ma[0] and self.fast_ma[-1] >= self.medium_ma[-1]
            
            # Signal 3: MACD histogram turns negative
            macd_exit = self.macd.macd[0] < self.macd.signal[0] and self.macd.macd[-1] >= self.macd.signal[-1]
            
            # If any exit signal is triggered, exit the market
            if rsi_exit or downtrend or macd_exit:
                signal_type = []
                if rsi_exit: signal_type.append("RSI Overbought")
                if downtrend: signal_type.append("Downtrend")
                if macd_exit: signal_type.append("MACD Exit")
                
                signal_str = ", ".join(signal_type)
                self.log(f'SELL SIGNAL: {signal_str}')
                self.log(f'SELL CREATE, {current_price:.2f}, RSI: {self.rsi[0]:.1f}')
                
                # Calculate position size to sell (all shares)
                size = self.position.size
                value = size * current_price
                self.log(f'Selling all {size} shares for approximately {value:.2f}')
                
                # Use close() to sell all shares
                self.order = self.close()


def run_backtest(data_file, start_cash=10000.0, commission=0.001, 
                fast_ma=10, medium_ma=30, rsi_period=14, 
                rsi_oversold=40, rsi_overbought=70, 
                trail_percent=0.07, risk_per_trade=0.5):
    """Run the backtest with the given parameters"""
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add the Market Momentum Strategy
    cerebro.addstrategy(MarketMomentumStrategy, 
                       fast_ma=fast_ma,
                       medium_ma=medium_ma,
                       rsi_period=rsi_period,
                       rsi_oversold=rsi_oversold,
                       rsi_overbought=rsi_overbought,
                       trail_percent=trail_percent,
                       risk_per_trade=risk_per_trade)
    
    # Set the default sizer to use percentage of available cash
    cerebro.addsizer(bt.sizers.PercentSizer, percents=risk_per_trade * 100)

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
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    # Print out the starting conditions
    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')

    # Run the backtest
    results = cerebro.run()
    
    # Print out the final result
    print(f'Final Portfolio Value: {cerebro.broker.getvalue():.2f}')
    
    # Print analyzer results
    strategy = results[0]
    print(f"Sharpe Ratio: {strategy.analyzers.sharpe.get_analysis().get('sharperatio', 0.0):.3f}")
    print(f"Max Drawdown: {strategy.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0.0):.2f}%")
    print(f"Total Return: {strategy.analyzers.returns.get_analysis().get('rtot', 0.0):.2f}%")
    
    # Print trade statistics
    trade_analysis = strategy.analyzers.trades.get_analysis()
    print(f"Total Trades: {trade_analysis.get('total', 0)}")
    print(f"Win Rate: {trade_analysis.get('won', 0) / trade_analysis.get('total', 1) * 100:.2f}% ({trade_analysis.get('won', 0)}/{trade_analysis.get('total', 0)})")
    
    # Plot the result
    cerebro.plot(style='candlestick', barup='green', bardown='red')
    
    return True


if __name__ == '__main__':
    import argparse
    import sys
    from data_handler import download_spy_data, check_and_fix_csv
    
    parser = argparse.ArgumentParser(description='Run Market Momentum Strategy Backtest')
    parser.add_argument('--data', type=str, default='spy_data.csv', help='Data file to use')
    parser.add_argument('--cash', type=float, default=10000.0, help='Starting cash')
    parser.add_argument('--commission', type=float, default=0.001, help='Commission rate')
    parser.add_argument('--fast-ma', type=int, default=10, help='Fast MA period')
    parser.add_argument('--medium-ma', type=int, default=30, help='Medium MA period')
    parser.add_argument('--rsi-period', type=int, default=14, help='RSI period')
    parser.add_argument('--rsi-oversold', type=int, default=40, help='RSI oversold threshold')
    parser.add_argument('--rsi-overbought', type=int, default=70, help='RSI overbought threshold')
    parser.add_argument('--trail-percent', type=float, default=0.07, help='Trailing stop percentage')
    parser.add_argument('--risk-per-trade', type=float, default=0.5, help='Risk per trade (0.5 = 50% of available cash)')
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
        fast_ma=args.fast_ma,
        medium_ma=args.medium_ma,
        rsi_period=args.rsi_period,
        rsi_oversold=args.rsi_oversold,
        rsi_overbought=args.rsi_overbought,
        trail_percent=args.trail_percent,
        risk_per_trade=args.risk_per_trade
    )
    
    if success:
        print("Backtest completed successfully")
        sys.exit(0)
    else:
        print("Backtest failed")
        sys.exit(1) 