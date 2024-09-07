from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import os

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def home():
    return "Combined YFinance API is running!"

@app.route('/api/stock/<ticker>', methods=['GET'])
def get_stock_data(ticker):
    try:
        # Fetch stock data
        stock = yf.Ticker(ticker)
        
        # Get historical data for the last 3 months
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        hist_data = stock.history(start=start_date, end=end_date)
        
        # Format historical data
        stock_data = [
            {"date": date.strftime('%Y-%m-%d'), "price": price} 
            for date, price in zip(hist_data.index, hist_data['Close'])
        ]
        
        # Get news
        news = stock.news[:5]
        formatted_news = [{"headline": item['title']} for item in news]
        
        
        insider_transactions = stock.insider_transactions
        insider_trades = []
        if not insider_transactions.empty:
            for _, transaction in insider_transactions.iterrows():
                insider_trades.append({
                    "insider": transaction['Insider'],
                    "shares": transaction['Shares']
                })
            insider_trades = insider_trades[:5]  # Limit to 5 most recent transactions
        
        # Get analyst recommendations
        recommendations = stock.recommendations
        if not recommendations.empty:
            latest_rec = recommendations.iloc[-1]
            analyst_ratings = {
                "buy": int(latest_rec.get('Strong Buy', 0) + latest_rec.get('Buy', 0)),
                "hold": int(latest_rec.get('Hold', 0)),
                "sell": int(latest_rec.get('Sell', 0) + latest_rec.get('Strong Sell', 0))
            }
        else:
            analyst_ratings = {"buy": 0, "hold": 0, "sell": 0}
        
        # Get last three financial statements
        income_stmt = stock.financials
        balance_sheet = stock.balance_sheet
        cash_flow = stock.cashflow
        
        financial_statements = {
            "income_statement": income_stmt.to_dict() if not income_stmt.empty else {},
            "balance_sheet": balance_sheet.to_dict() if not balance_sheet.empty else {},
            "cash_flow": cash_flow.to_dict() if not cash_flow.empty else {}
        }
        
        return jsonify({
            "stockData": stock_data,
            "news": formatted_news,
            "insiderSales": insider_trades,
            "analystRatings": analyst_ratings,
            "financialStatements": financial_statements
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400

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
