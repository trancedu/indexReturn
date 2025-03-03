# SPY Trading Strategies Backtester
A comprehensive backtesting framework for various trading strategies on the S&P 500 ETF (SPY) using the Backtrader library. This project implements and tests multiple trading strategies with customizable parameters and detailed performance analysis.

# Statistics
| Strategy            | Average Annual Return | Final Cumulative Return | Annualized Return | Standard Deviation | Worst Year | Best Year |
|---------------------|-----------------------|-------------------------|-------------------|--------------------|------------|-----------|
| Regular Returns     | 11.68%                | 17.648756               | 10.04%            | 18.27%             | -36.79%    | 38.05%    |
| Without Top 1 Day   | 7.54%                 | 5.309419                | 5.72%             | 18.59%             | -44.81%    | 35.23%    |
| Without Top 2 Days  | 4.29%                 | 1.985494                | 2.31%             | 18.87%             | -50.58%    | 33.26%    |
| Without Top 3 Days  | 1.52%                 | 0.845171                | -0.56%            | 19.05%             | -53.79%    | 31.40%    |
| Without Top 4 Days  | -0.90%                | 0.389561                | -3.09%            | 19.23%             | -56.50%    | 29.56%    |


## Available Strategies

### 1. Buy and Hold Strategy
A baseline strategy that buys SPY with all available cash on the first day and holds until the end of the testing period.

```bash
python runners/run_buy_and_hold.py [options]
```

### 2. SMA Crossover Strategy
A trend-following strategy that uses two Simple Moving Averages (fast and slow) to generate buy/sell signals.

```bash
python runners/run_sma.py --fast 50 --slow 200 [options]
```

Parameters:
- `--fast`: Fast SMA period (default: 50)
- `--slow`: Slow SMA period (default: 200)

### 3. Market Momentum Strategy
An aggressive strategy that combines multiple technical indicators (RSI, MACD, Moving Averages) for trading decisions.

```bash
python runners/run_momentum.py [options]
```

Parameters:
- `--fast-ma`: Fast moving average period (default: 10)
- `--medium-ma`: Medium moving average period (default: 20)
- `--rsi-period`: RSI calculation period (default: 14)
- `--rsi-oversold`: RSI oversold threshold (default: 30)
- `--rsi-overbought`: RSI overbought threshold (default: 70)
- `--trail-percent`: Trailing stop percentage (default: 0.05)
- `--risk-per-trade`: Risk per trade as fraction of portfolio (default: 0.02)

### 4. Rebound Strategy
A mean-reversion strategy that looks for significant price drops followed by rebounds.

```bash
python runners/run_rebound.py [options]
```

Parameters:
- `--drop`: Drop threshold (default: 0.10 for 10%)
- `--rise`: Rise threshold (default: 0.20 for 20%)
- `--lookback`: Lookback period in days (default: 5)

## Common Options for All Strategies

All strategy runners support the following common options:

```bash
--data DATA             Data file to use (default: spy_data.csv)
--output OUTPUT         Output file for results (default: strategy_results.csv)
--cash CASH            Starting cash amount (default: 10000.0)
--commission COMM      Commission rate (default: 0.001)
--no-plot             Disable plotting
--download            Download fresh SPY data
--start-date DATE     Start date for data download (default: 2000-01-01)
--end-date DATE       End date for data download (default: 2023-12-31)
```

## Project Structure

```
├── strategy_runner.py          # Shared backtest functionality
├── data_handler.py            # Data download and preprocessing
├── strategies/                # Strategy implementations
│   ├── __init__.py
│   ├── buy_and_hold_strategy.py
│   ├── sma_crossover_strategy.py
│   ├── market_momentum_strategy.py
│   └── rebound_strategy.py
├── runners/                   # Strategy runner scripts
│   ├── __init__.py
│   ├── run_buy_and_hold.py
│   ├── run_sma.py            # SMA Crossover runner
│   ├── run_momentum.py
│   └── run_rebound.py
├── requirements.txt           # Python dependencies
└── README.md                 # This file
```

## Features

- **Data Management**: Automatic download of SPY historical data
- **Performance Metrics**: 
  - Sharpe Ratio
  - Maximum Drawdown
  - Total Return
  - Trade Statistics (win rate, number of trades)
- **Visualization**: Candlestick charts with strategy indicators
- **CSV Export**: Detailed trade data and performance metrics
- **Modular Design**: Easy to add new strategies

## Requirements

- Python 3.7+
- backtrader
- pandas
- matplotlib
- yfinance (for data download)

Install dependencies:
```bash
pip install -r requirements.txt
```

## Example Usage

1. Download fresh SPY data and run the SMA Crossover strategy:
```bash
python runners/run_sma.py --download --fast 50 --slow 200
```

2. Run the Market Momentum strategy with custom parameters:
```bash
python runners/run_momentum.py --rsi-oversold 35 --rsi-overbought 65 --trail-percent 0.03
```

3. Compare strategies by running them on the same data:
```bash
python runners/run_buy_and_hold.py --data spy_data.csv
python runners/run_sma.py --data spy_data.csv
python runners/run_momentum.py --data spy_data.csv
python runners/run_rebound.py --data spy_data.csv
```

## Performance Analysis

Each strategy run generates:
1. A CSV file with detailed trade data and performance metrics
2. Console output with key performance indicators
3. Interactive plots showing price action and strategy signals

## Contributing

Feel free to contribute by:
1. Adding new strategies
2. Improving existing strategies
3. Enhancing the analysis tools
4. Reporting bugs or suggesting improvements

To add a new strategy:
1. Create a new strategy file in `strategies/`
2. Create a new runner file in `runners/`
3. Follow the existing pattern for strategy implementation and runner setup
4. Update this README with the new strategy's details

## License

MIT License - feel free to use this code for any purpose.