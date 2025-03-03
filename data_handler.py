#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Data Handler for SMA Crossover Strategy
Handles downloading and processing of financial data
"""

import pandas as pd
import yfinance as yf

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

def check_and_fix_csv(csv_file):
    """
    Check if the CSV file has the correct format and fix it if needed
    """
    import os
    
    if not os.path.exists(csv_file):
        print(f"Error: CSV file {csv_file} does not exist")
        return False
    
    try:
        # Try to read the file with pandas
        df = pd.read_csv(csv_file)
        
        print(f"CSV file structure:")
        print(df.head(2))
        
        # Check for required columns
        required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"Error: Missing required columns: {missing_cols}")
            return False
            
        # Add OpenInterest if missing
        if 'OpenInterest' not in df.columns:
            df['OpenInterest'] = 0
            df.to_csv(csv_file, index=False)
            print("Added OpenInterest column")
        
        return True
        
    except Exception as e:
        print(f"Error checking CSV file: {e}")
        return False 