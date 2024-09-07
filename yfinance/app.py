from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
import os

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def home():
    return "YFinance API is running!"

@app.route('/backtest', methods=['POST'])
def backtest():
    data = request.json
    portfolio = data['portfolio']
    start_date = data['startDate']
    end_date = data['endDate']

    try:
        # Fetch data for each stock in the portfolio
        portfolio_data = {}
        for stock in portfolio:
            ticker = yf.Ticker(stock['ticker'])
            hist = ticker.history(start=start_date, end=end_date)
            portfolio_data[stock['ticker']] = hist['Close']

        # Fetch S&P 500 data
        sp500 = yf.Ticker("^GSPC")
        sp500_data = sp500.history(start=start_date, end=end_date)['Close']

        # Calculate portfolio value
        portfolio_value = sum(portfolio_data[stock['ticker']] * stock['shares'] for stock in portfolio)

        # Prepare performance data
        performance_data = []
        for date in portfolio_value.index:
            performance_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'portfolioValue': portfolio_value[date],
                'sp500Value': sp500_data[date]
            })

        # Calculate returns
        portfolio_return = (portfolio_value[-1] / portfolio_value[0] - 1) * 100
        sp500_return = (sp500_data[-1] / sp500_data[0] - 1) * 100

        # Calculate Sharpe ratios
        risk_free_rate = 0.02  # Assume 2% risk-free rate
        portfolio_sharpe_ratio = calculate_sharpe_ratio(portfolio_value, risk_free_rate)
        sp500_sharpe_ratio = calculate_sharpe_ratio(sp500_data, risk_free_rate)

        return jsonify({
            'performanceData': performance_data,
            'portfolioReturn': portfolio_return,
            'sp500Return': sp500_return,
            'portfolioSharpeRatio': portfolio_sharpe_ratio,
            'sp500SharpeRatio': sp500_sharpe_ratio
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

def calculate_sharpe_ratio(returns, risk_free_rate):
    daily_returns = returns.pct_change().dropna()
    excess_returns = daily_returns - risk_free_rate / 252  # Assuming 252 trading days in a year
    return np.sqrt(252) * excess_returns.mean() / excess_returns.std()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)