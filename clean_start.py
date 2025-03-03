#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Clean Start Script for SMA Crossover Strategy
Deletes existing files and runs the analysis with clean files
"""

import os
import subprocess
import sys
import time
from data_handler import download_spy_data

def main():
    print("Starting clean run of SMA Crossover Strategy...")
    
    # Define file paths
    data_file = "spy_data.csv"
    results_file = "backtest_results.csv"
    
    # Delete existing files if they exist
    print("Cleaning up existing files...")
    for file_path in [data_file, results_file]:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Removed {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")
    
    # Download fresh data
    print("Downloading fresh data...")
    start_date = "2000-01-01"
    end_date = "2023-12-31"
    if not download_spy_data(start_date, end_date, data_file):
        print("Error: Failed to download data")
        return
    
    # Build the command
    cmd = [
        sys.executable,  # Use the current Python interpreter
        "run_backtest.py",
        "--data", data_file,
        "--output", results_file
    ]
    
    # Run the command
    print("Running analysis with clean files...")
    start_time = time.time()
    result = subprocess.run(cmd)
    end_time = time.time()
    
    # Check if the analysis was successful
    if result.returncode == 0 and os.path.exists(results_file):
        print(f"Analysis completed successfully in {end_time - start_time:.2f} seconds!")
        print(f"Results saved to {results_file}")
    else:
        print("Analysis failed. Check the error messages above.")
    
    print("Clean start completed!")

if __name__ == "__main__":
    main() 