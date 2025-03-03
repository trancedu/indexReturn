#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Run the Market Momentum Strategy backtest and save results to CSV
"""

import datetime
import os.path
import pandas as pd
import argparse
import sys

import backtrader as bt
from market_momentum_strategy import MarketMomentumStrategy
from data_handler import download_spy_data, check_and_fix_csv


class CSVWriter(bt.Analyzer):
    """Analyzer to save trade data to CSV"""
    
    params = (
        ('filename', 'momentum_results.csv'),
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
        
        # Get indicator values
        fast_ma = self.strategy.fast_ma[0] if hasattr(self.strategy, 'fast_ma') else float('nan')
        medium_ma = self.strategy.medium_ma[0] if hasattr(self.strategy, 'medium_ma') else float('nan')
        rsi = self.strategy.rsi[0] if hasattr(self.strategy, 'rsi') else float('nan')
        macd = self.strategy.macd.macd[0] if hasattr(self.strategy, 'macd') else float('nan')
        macd_signal = self.strategy.macd.signal[0] if hasattr(self.strategy, 'macd') else float('nan')
        
        # Get trailing stop if available
        trailing_stop = self.strategy.trailing_stop if hasattr(self.strategy, 'trailing_stop') and self.strategy.trailing_stop else float('nan')
        
        # Get cash
        cash = self.strategy.broker.getcash()
        
        # Store the results
        self.results.append({
            'Date': date.isoformat(),
            'Close': close,
            'FastMA': fast_ma,
            'MediumMA': medium_ma,
            'RSI': rsi,
            'MACD': macd,
            'MACD_Signal': macd_signal,
            'Position': position,
            'TrailingStop': trailing_stop,
            'Cash': cash,
            'PortfolioValue': portfolio_value
        })
    
    def stop(self):
        # Convert results to DataFrame and save to CSV
        results_df = pd.DataFrame(self.results)
        results_df.to_csv(self.p.filename, index=False)
        print(f"Results saved to {self.p.filename}")


def run_backtest(data_file, output_file='momentum_results.csv', start_cash=10000.0, commission=0.001,
                fast_ma=10, medium_ma=30, rsi_period=14, 
                rsi_oversold=40, rsi_overbought=70, 
                trail_percent=0.07, risk_per_trade=0.5, plot=True):
    """
    Run the Market Momentum Strategy backtest and save results to CSV
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
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
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
        
        # Print trade statistics
        trade_analysis = strategy.analyzers.trades.get_analysis()
        try:
            # Extract values safely from the AutoOrderedDict
            total_trades = trade_analysis.total.total if hasattr(trade_analysis, 'total') and hasattr(trade_analysis.total, 'total') else 0
            won_trades = trade_analysis.won.total if hasattr(trade_analysis, 'won') and hasattr(trade_analysis.won, 'total') else 0
            
            # Calculate win rate only if we have trades
            win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
            
            print(f"Total Trades: {total_trades}")
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Market Momentum Strategy Backtest')
    parser.add_argument('--data', type=str, default='spy_data.csv', help='Data file to use')
    parser.add_argument('--output', type=str, default='momentum_results.csv', help='Output file for results')
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
    
    # Run the backtest
    success = run_backtest(
        data_file=data_file,
        output_file=args.output,
        start_cash=args.cash,
        commission=args.commission,
        fast_ma=args.fast_ma,
        medium_ma=args.medium_ma,
        rsi_period=args.rsi_period,
        rsi_oversold=args.rsi_oversold,
        rsi_overbought=args.rsi_overbought,
        trail_percent=args.trail_percent,
        risk_per_trade=args.risk_per_trade,
        plot=not args.no_plot
    )
    
    if success:
        print("Backtest completed successfully")
        sys.exit(0)
    else:
        print("Backtest failed")
        sys.exit(1) 