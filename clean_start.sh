#!/bin/bash

# Clean start script for SMA Crossover Strategy

echo "Starting clean run of SMA Crossover Strategy..."

# Define file paths
DATA_FILE="spy_data_clean.csv"
RESULTS_FILE="backtest_results_clean.csv"

# Delete existing files if they exist
echo "Cleaning up existing files..."
if [ -f "$DATA_FILE" ]; then
    echo "Removing $DATA_FILE"
    rm -f "$DATA_FILE"
fi

if [ -f "$RESULTS_FILE" ]; then
    echo "Removing $RESULTS_FILE"
    rm -f "$RESULTS_FILE"
fi

# Run the analysis with clean files
echo "Running analysis with clean files..."
python run_analysis.py --force-download --data "$DATA_FILE" --output "$RESULTS_FILE"

# Check if the analysis was successful
if [ -f "$RESULTS_FILE" ]; then
    echo "Analysis completed successfully!"
    echo "Results saved to $RESULTS_FILE"
else
    echo "Analysis failed. Check the error messages above."
fi

echo "Clean start completed!" 