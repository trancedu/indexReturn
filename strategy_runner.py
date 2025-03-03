#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Base Strategy Runner Module
Contains common functionality for running different trading strategies
"""

import datetime
import os.path
import pandas as pd
import argparse
import sys

import backtrader as bt
from data_handler import download_spy_data, check_and_fix_csv


class CSVWriter(bt.Analyzer):
    """Analyzer to save trade data to CSV"""
    
    params = (
        ('filename', 'strategy_results.csv'),
        ('extra_fields', []),  # List of tuples (field_name, getter_function)
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
        
        # Get cash
        cash = self.strategy.broker.getcash()
        
        # Create base result dict
        result = {
            'Date': date.isoformat(),
            'Close': close,
            'Position': position,
            'Cash': cash,
            'PortfolioValue': portfolio_value
        }
        
        # Add extra fields if specified
        for field_name, getter_func in self.p.extra_fields:
            try:
                result[field_name] = getter_func(self.strategy)
            except Exception:
                result[field_name] = float('nan')
        
        # Store the results
        self.results.append(result)
    
    def stop(self):
        # Convert results to DataFrame and save to CSV
        results_df = pd.DataFrame(self.results)
        results_df.to_csv(self.p.filename, index=False)
        print(f"Results saved to {self.p.filename}")


def run_strategy_backtest(strategy_class, data_file, output_file='strategy_results.csv', 
                         start_cash=10000.0, commission=0.001, plot=True,
                         strategy_params=None, extra_analyzers=None, csv_fields=None):
    """
    Run a strategy backtest and save results to CSV
    
    Parameters:
    - strategy_class: The strategy class to backtest
    - data_file: Path to the data file
    - output_file: Path to save results
    - start_cash: Initial cash amount
    - commission: Commission rate
    - plot: Whether to plot results
    - strategy_params: Dict of strategy-specific parameters
    - extra_analyzers: Dict of additional analyzers to add
    - csv_fields: List of tuples (field_name, getter_function) for additional CSV fields
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
        
        # Add the strategy with parameters if provided
        if strategy_params:
            cerebro.addstrategy(strategy_class, **strategy_params)
        else:
            cerebro.addstrategy(strategy_class)
        
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
        
        # Add default analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        # Add CSV writer with extra fields if provided
        cerebro.addanalyzer(CSVWriter, _name='csvwriter', 
                           filename=output_file,
                           extra_fields=csv_fields or [])
        
        # Add extra analyzers if provided
        if extra_analyzers:
            for name, analyzer in extra_analyzers.items():
                cerebro.addanalyzer(analyzer, _name=name)
        
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
        
        # Print trade statistics
        trade_analysis = strategy.analyzers.trades.get_analysis()
        try:
            # Extract values safely from the AutoOrderedDict
            total_trades = trade_analysis.total.total if hasattr(trade_analysis, 'total') and hasattr(trade_analysis.total, 'total') else 0
            won_trades = trade_analysis.won.total if hasattr(trade_analysis, 'won') and hasattr(trade_analysis.won, 'total') else 0
            
            print(f"Total Trades: {total_trades}")
            if total_trades > 0:
                win_rate = (won_trades / total_trades * 100)
                print(f"Win Rate: {win_rate:.2f}% ({won_trades}/{total_trades})")
        except Exception as e:
            print(f"Could not calculate trade statistics: {e}")
            print("Trade analysis data:", trade_analysis)
        
        # Plot the result if requested
        if plot:
            cerebro.plot(style='candlestick', barup='green', bardown='red')
        
        print(f"Backtest results saved to {output_file}")
        return True
        
    except Exception as e:
        print(f"Error running backtest: {e}")
        return False


def parse_common_args():
    """Parse common command line arguments for strategy runners"""
    parser = argparse.ArgumentParser(description='Run Strategy Backtest')
    parser.add_argument('--data', type=str, default='spy_data.csv', help='Data file to use')
    parser.add_argument('--output', type=str, default='strategy_results.csv', help='Output file for results')
    parser.add_argument('--cash', type=float, default=10000.0, help='Starting cash')
    parser.add_argument('--commission', type=float, default=0.001, help='Commission rate')
    parser.add_argument('--no-plot', action='store_true', help='Disable plotting')
    parser.add_argument('--download', action='store_true', help='Download fresh data')
    parser.add_argument('--start-date', type=str, default='2000-01-01', help='Start date for data download')
    parser.add_argument('--end-date', type=str, default='2023-12-31', help='End date for data download')
    
    return parser 