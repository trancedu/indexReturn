#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Visualization script for the SMA Crossover Strategy results
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import argparse


def plot_equity_curve(results_file):
    """Plot the equity curve from the results CSV file"""
    if not os.path.exists(results_file):
        print(f"Results file {results_file} not found.")
        return
    
    # Load results
    df = pd.read_csv(results_file, parse_dates=['date'])
    df.set_index('date', inplace=True)
    
    # Create figure
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [3, 1, 1]})
    
    # Plot portfolio value
    axes[0].plot(df.index, df['portfolio_value'], label='Portfolio Value', linewidth=2)
    axes[0].set_title('SMA Crossover Strategy Performance')
    axes[0].set_ylabel('Portfolio Value ($)')
    axes[0].grid(True)
    axes[0].legend()
    
    # Plot drawdown
    df['drawdown'] = (df['portfolio_value'].cummax() - df['portfolio_value']) / df['portfolio_value'].cummax() * 100
    axes[1].fill_between(df.index, df['drawdown'], 0, color='red', alpha=0.3)
    axes[1].set_ylabel('Drawdown (%)')
    axes[1].grid(True)
    
    # Plot buy/sell signals
    if 'signal' in df.columns:
        buy_signals = df[df['signal'] == 1]
        sell_signals = df[df['signal'] == -1]
        
        axes[2].plot(df.index, df['close'], label='SPY Price', alpha=0.5)
        axes[2].scatter(buy_signals.index, buy_signals['close'], marker='^', color='green', label='Buy Signal')
        axes[2].scatter(sell_signals.index, sell_signals['close'], marker='v', color='red', label='Sell Signal')
        axes[2].set_ylabel('Price ($)')
        axes[2].grid(True)
        axes[2].legend()
    
    plt.tight_layout()
    plt.savefig('strategy_performance.png', dpi=300)
    plt.show()


def calculate_performance_metrics(results_file):
    """Calculate and print performance metrics"""
    if not os.path.exists(results_file):
        print(f"Results file {results_file} not found.")
        return
    
    # Load results
    df = pd.read_csv(results_file, parse_dates=['date'])
    df.set_index('date', inplace=True)
    
    # Calculate daily returns
    df['daily_return'] = df['portfolio_value'].pct_change()
    
    # Calculate metrics
    total_return = (df['portfolio_value'].iloc[-1] / df['portfolio_value'].iloc[0] - 1) * 100
    annual_return = (1 + total_return/100) ** (252 / len(df)) - 1
    annual_return *= 100  # Convert to percentage
    
    volatility = df['daily_return'].std() * np.sqrt(252) * 100
    sharpe_ratio = annual_return / volatility if volatility > 0 else 0
    
    max_drawdown = (df['portfolio_value'].cummax() - df['portfolio_value']).max() / df['portfolio_value'].cummax() * 100
    
    # Print metrics
    print("\n===== Performance Metrics =====")
    print(f"Total Return: {total_return:.2f}%")
    print(f"Annualized Return: {annual_return:.2f}%")
    print(f"Annualized Volatility: {volatility:.2f}%")
    print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"Maximum Drawdown: {max_drawdown:.2f}%")
    print("===============================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Visualize backtest results')
    parser.add_argument('--results', type=str, default='backtest_results.csv',
                        help='Path to the results CSV file')
    args = parser.parse_args()
    
    calculate_performance_metrics(args.results)
    plot_equity_curve(args.results) 