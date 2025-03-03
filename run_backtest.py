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
        return False
    
    try:
        # Try to read the file with pandas
        df = pd.read_csv(csv_file)
        
        print(f"CSV file structure before fixing:")
        print(df.head(2))
        
        # Check for multi-index-like structure (rows with column names)
        if len(df) >= 2:
            first_row = df.iloc[0]
            # If the first row contains strings like 'SPY' or column names, it might be a header row
            if all(isinstance(val, str) and val in ['SPY', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume'] 
                  for val in first_row if isinstance(val, str)):
                print("Detected multi-index-like structure. Removing header rows...")
                # Get the actual column names from the CSV
                actual_cols = df.columns.tolist()
                
                # Find the first row with actual data (usually after the header rows)
                data_start_idx = 0
                for i in range(len(df)):
                    row = df.iloc[i]
                    # Check if this row has a date-like value in the first column
                    if isinstance(row[0], str) and len(row[0]) >= 8 and '-' in row[0]:
                        data_start_idx = i
                        break
                
                if data_start_idx > 0:
                    print(f"Found data starting at row {data_start_idx}")
                    # Create a new DataFrame with only the data rows
                    df = df.iloc[data_start_idx:].reset_index(drop=True)
                    
                    # Rename columns to standard names if needed
                    if 'Date' not in df.columns:
                        # Try to find the date column
                        date_col = None
                        for col in df.columns:
                            if df[col].dtype == 'object' and all('-' in str(val) for val in df[col].dropna()):
                                date_col = col
                                break
                        
                        if date_col:
                            # Create a mapping of current columns to standard names
                            col_mapping = {}
                            std_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
                            
                            # Map the date column
                            col_mapping[date_col] = 'Date'
                            
                            # Try to map the remaining columns
                            remaining_cols = [col for col in df.columns if col != date_col]
                            for i, col in enumerate(remaining_cols):
                                if i < len(std_cols) - 1:  # Skip 'Date' which we already mapped
                                    col_mapping[col] = std_cols[i + 1]
                            
                            # Rename the columns
                            df = df.rename(columns=col_mapping)
        
        # Check if we have the necessary columns
        required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"CSV file {csv_file} is missing required columns: {missing_cols}")
            return False
        
        # Check for empty date values or other issues
        if df['Date'].isna().any() or df['Date'].eq('').any():
            print(f"CSV file {csv_file} has empty date values. Cleaning...")
            df = df.dropna(subset=['Date'])
            df = df[df['Date'] != '']
        
        # Ensure Date is in the correct format
        try:
            # Try to parse dates
            pd.to_datetime(df['Date'])
        except:
            print(f"CSV file {csv_file} has date format issues.")
            return False
        
        # Add OpenInterest column if missing
        if 'OpenInterest' not in df.columns:
            df['OpenInterest'] = 0
        
        # Save the fixed file
        df.to_csv(csv_file, index=False)
        print(f"Fixed CSV file {csv_file}")
        
        # Verify the file
        print(f"Verifying CSV file format...")
        with open(csv_file, 'r') as f:
            first_lines = [next(f) for _ in range(min(5, len(df) + 1))]
        print(f"First few lines of {csv_file}:")
        for line in first_lines:
            print(f"  {line.strip()}")
        
        return True
        
    except Exception as e:
        import traceback
        print(f"Error checking/fixing CSV file: {e}")
        print(traceback.format_exc())
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
    """Run the backtest with the given parameters and save results to CSV"""
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(SmaCrossStrategy, 
                        fast_period=fast_period, 
                        slow_period=slow_period)

    # First check if the CSV file exists and has the right format
    if not os.path.exists(data_file):
        print(f"Error: Data file {data_file} does not exist.")
        return False
    
    # Verify the CSV file format
    try:
        df = pd.read_csv(data_file)
        print(f"CSV file structure for backtest:")
        print(df.head(2))
        
        # Check required columns
        required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"Error: CSV file is missing required columns: {missing_cols}")
            return False
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return False

    # Load the data
    try:
        data = bt.feeds.GenericCSVData(
            dataname=data_file,
            # Do not pass values before this date
            fromdate=datetime.datetime(1993, 1, 1),
            # Do not pass values after this date
            todate=datetime.datetime(2023, 12, 31),
            
            # CSV format specifications
            dtformat='%Y-%m-%d',      # Date format
            datetime=0,               # Date is in the first column
            open=1,                   # Open price is in the second column
            high=2,                   # High price is in the third column
            low=3,                    # Low price is in the fourth column
            close=4,                  # Close price is in the fifth column
            volume=5,                 # Volume is in the sixth column
            openinterest=6,           # OpenInterest is in the seventh column
            
            # Skip the header row
            headers=True,
            
            # Additional settings
            nullvalue=0.0,            # Value to use for missing data
            skiprows=0,               # Number of rows to skip
            separator=',',            # CSV separator
        )

        # Add the Data Feed to Cerebro
        cerebro.adddata(data)
    except Exception as e:
        import traceback
        print(f"Error loading data: {e}")
        print(traceback.format_exc())
        return False

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
    try:
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
        
        return True
    except Exception as e:
        import traceback
        print(f"Error running backtest: {e}")
        print(traceback.format_exc())
        return False


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
        if data_file is None:
            print(f"Failed to download or process data. Exiting.")
            sys.exit(1)
    else:
        # Check if the existing file has the correct format
        if not check_and_fix_csv(data_file):
            print(f"Existing file {data_file} has incorrect format and could not be fixed.")
            print("Downloading fresh data...")
            data_file = download_spy_data(start_date, end_date, data_file)
            if data_file is None:
                print(f"Failed to download or process data. Exiting.")
                sys.exit(1)
    
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
    
    if not success:
        print("Backtest failed. Check the error messages above.")
        sys.exit(1)
    
    print(f"Backtest completed successfully. Results saved to {args.output}")
    sys.exit(0) 