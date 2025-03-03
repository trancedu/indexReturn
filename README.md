# This is a collection of scripts and notebooks for analyzing and trading stocks.

# Statistics
| Strategy            | Average Annual Return | Final Cumulative Return | Annualized Return | Standard Deviation | Worst Year | Best Year |
|---------------------|-----------------------|-------------------------|-------------------|--------------------|------------|-----------|
| Regular Returns     | 11.68%                | 17.648756               | 10.04%            | 18.27%             | -36.79%    | 38.05%    |
| Without Top 1 Day   | 7.54%                 | 5.309419                | 5.72%             | 18.59%             | -44.81%    | 35.23%    |
| Without Top 2 Days  | 4.29%                 | 1.985494                | 2.31%             | 18.87%             | -50.58%    | 33.26%    |
| Without Top 3 Days  | 1.52%                 | 0.845171                | -0.56%            | 19.05%             | -53.79%    | 31.40%    |
| Without Top 4 Days  | -0.90%                | 0.389561                | -3.09%            | 19.23%             | -56.50%    | 29.56%    |



# Conclusion
* Missing the top 1 day of returns has a big impact on the performance of the strategy.
* Missing the top 2 days of returns will eliminate equities advantage over bonds.

# SMA Crossover Strategy Backtest

This project implements a simple moving average (SMA) crossover strategy for the SPY ETF over a 30-year period using Backtrader.

## Strategy Description

The strategy uses two simple moving averages:
- Fast SMA (default: 50 days)
- Slow SMA (200 days)

Trading rules:
- Buy when the fast SMA crosses above the slow SMA
- Sell when the fast SMA crosses below the slow SMA

## Project Structure

- `sma_crossover_strategy.py`: Contains the main strategy implementation
- `run_backtest.py`: Script to run the backtest and save results to CSV
- `visualize_results.py`: Script to visualize the backtest results

## Setup Environment

### Using Conda

```bash
# Create a new conda environment
conda create -n backtrader python=3.8
conda activate backtrader

# Install required packages
conda install -c conda-forge pandas matplotlib numpy
conda install -c conda-forge backtrader
conda install -c conda-forge yfinance
```

### Using pip

```bash
# Create a virtual environment
python -m venv backtrader_env
source backtrader_env/bin/activate  # On Windows: backtrader_env\Scripts\activate

# Install required packages
pip install backtrader pandas matplotlib numpy yfinance
```

## Usage

### Running the Backtest

```bash
# Run with default parameters
python run_backtest.py

# Run with custom parameters
python run_backtest.py --cash 100000 --commission 0.0005 --fast 20 --slow 100
```

### Command Line Arguments

- `--data`: Path to the data CSV file (default: 'spy_data.csv')
- `--output`: Path to save the results CSV file (default: 'backtest_results.csv')
- `--cash`: Initial cash amount (default: 10000.0)
- `--commission`: Commission rate (default: 0.001)
- `--fast`: Fast SMA period (default: 50)
- `--slow`: Slow SMA period (default: 200)
- `--no-plot`: Disable plotting

### Visualizing Results

```bash
# Visualize the backtest results
python visualize_results.py

# Visualize custom results file
python visualize_results.py --results custom_results.csv
```

## Example Output

The backtest will generate:
1. Performance metrics in the console
2. A CSV file with detailed results
3. A plot showing the equity curve, drawdown, and buy/sell signals

## License

This project is open-source and available under the MIT License.