#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Run the entire SMA Crossover Strategy workflow:
1. Download data
2. Run backtest
3. Visualize results
"""

import os
import argparse
import subprocess
import datetime

def main():
    parser = argparse.ArgumentParser(description='Run SMA Crossover Strategy Analysis')
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
    parser.add_argument('--data', type=str, default='spy_data.csv',
                        help='Path to the data CSV file')
    parser.add_argument('--output', type=str, default='backtest_results.csv',
                        help='Path to save the results CSV file')
    parser.add_argument('--force-download', action='store_true',
                        help='Force re-download of data even if file exists')
    args = parser.parse_args()
    
    print("=" * 50)
    print("SMA Crossover Strategy Analysis")
    print("=" * 50)
    
    # Step 1: Run backtest
    print("\nRunning backtest...")
    backtest_cmd = [
        "python", "run_backtest.py",
        "--cash", str(args.cash),
        "--commission", str(args.commission),
        "--fast", str(args.fast),
        "--slow", str(args.slow),
        "--data", args.data,
        "--output", args.output
    ]
    
    if args.no_plot:
        backtest_cmd.append("--no-plot")
        
    if args.force_download:
        backtest_cmd.append("--force-download")
    
    backtest_result = subprocess.run(backtest_cmd)
    
    # Only proceed with visualization if backtest was successful
    if backtest_result.returncode == 0 and os.path.exists(args.output):
        # Step 2: Visualize results
        print("\nVisualizing results...")
        visualize_cmd = [
            "python", "visualize_results.py",
            "--results", args.output
        ]
        
        subprocess.run(visualize_cmd)
        
        print("\nAnalysis complete!")
        print(f"Results saved to {args.output}")
        print(f"Visualization saved to strategy_performance.png")
    else:
        print("\nBacktest failed or no results file was generated.")
        print("Please check the error messages above.")
    
    print("=" * 50)

if __name__ == "__main__":
    main() 