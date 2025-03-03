#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple Buy and Hold Strategy for SPY
This strategy:
1. Buys SPY with all available cash on the first day
2. Holds the position until the end of the backtest period
"""

import backtrader as bt

class BuyAndHoldStrategy(bt.Strategy):
    """
    Simple Buy and Hold Strategy
    - Buy on the first day with all available cash
    - Hold until the end of the backtest period
    """
    
    def __init__(self):
        """Initialize the strategy"""
        self.dataclose = self.datas[0].close
        self.order = None
        self.bought = False
        
    def log(self, txt, dt=None):
        """Logging function"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')
        
    def notify_order(self, order):
        """
        Receives notifications for orders
        """
        if order.status in [order.Submitted, order.Accepted]:
            # Order submitted/accepted - nothing to do
            return
            
        # Check if an order has been completed
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, {order.executed.price:.2f}, Size: {order.executed.size}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            else:
                self.log(f'SELL EXECUTED, {order.executed.price:.2f}, Size: {order.executed.size}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
            
        self.order = None
        
    def next(self):
        """
        Main strategy logic
        - Buy on first opportunity with all available cash
        - Hold position until the end
        """
        # Check if we are already in the market
        if self.bought:
            return
            
        # If we have no position and haven't bought yet, BUY!
        if not self.position and not self.bought:
            # Calculate the max number of shares we can buy
            cash = self.broker.getcash()
            price = self.dataclose[0]
            size = int(cash / price)
            
            self.log(f'BUY CREATE, {price:.2f}, Using {cash:.2f} to buy {size} shares')
            self.order = self.buy(size=size)
            self.bought = True 