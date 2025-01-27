from flask import Flask, request, jsonify, render_template, send_file
import pandas as pd
import yfinance as yf
import pandas_ta as ta
from datetime import datetime, timedelta
import json
import os

# Initialize Flask app
app = Flask(__name__)

# Nifty 50 stock tickers (list for dropdown)
nifty_50_tickers = [
    "TCS.NS", "INFY.NS", "HDFC.NS", "RELIANCE.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "KOTAKBANK.NS", "BAJFINANCE.NS", "SBIN.NS", "ASIANPAINT.NS"
]

# Function to fetch stock data and calculate indicators
def fetch_data(ticker):
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        data = yf.download(ticker, start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
        
        # Check if data is empty
        if data.empty:
            raise ValueError(f"No data available for {ticker}.")
        
        # Flatten multi-level columns (if applicable)
        data.columns = data.columns.get_level_values(0)

        # Calculate RSI
        data['RSI'] = ta.rsi(data['Close'], length=14)

        # Calculate MACD
        macd = ta.macd(data['Close'], fast=12, slow=26, signal=9)
        if macd is not None:
            data['MACD'] = macd['MACD_12_26_9']
            data['MACD_Signal'] = macd['MACDs_12_26_9']
            data['MACD_Histogram'] = macd['MACDh_12_26_9']
        else:
            raise ValueError("MACD calculation failed.")

        # Calculate SMA/EMA
        data['SMA_20'] = ta.sma(data['Close'], length=20)
        data['EMA_10'] = ta.ema(data['Close'], length=10)

        # Drop rows with NaN values
        data.dropna(inplace=True)

        return data.tail(5)

    except Exception as e:
        print(f"Error while fetching data for {ticker}: {e}")
        return None

# Function to generate and save the JSON data
def save_to_json(ticker, data):
    analysis_text = {
        "Analysis": "Act like a stock option trading expert for the Indian stock market.\n"
                    "I will give you technical data of a stock for the last 5 trading sessions. "
                    "You need to analyze the trend based on the last 5 days and also analyze the technical tools "
                    "like values of each tool (increased or decreased) and its current value, what may happen with its probability. "
                    "Also, search for the latest option chain data of the stock if available and give an overall recommendation.\n"
                    "The recommendation should be based on a strategy - proper strategy with entry and exits and what to do if gone in favor or if in reverse direction how to manage"
    }

    # Combine the analysis text and stock data
    combined_data = {
        "Analysis": analysis_text["Analysis"],
        "StockData": data.to_dict(orient='records')  # Convert DataFrame to list of dicts
    }

    # Save the combined data as a JSON file (including the analysis text)
    json_filename = f"{ticker}_tech_data.json"
    with open(json_filename, 'w') as f:
        json.dump(combined_data, f, indent=4)

    return json_filename, combined_data

# Home page route
@app.route('/')
def home():
    return render_template('index.html', tickers=nifty_50_tickers)

# Fetch stock data route
@app.route('/fetch', methods=['POST'])
def fetch():
    ticker = request.form['ticker']
    data = fetch_data(ticker)
    
    if data is None:
        return f"<p>Error: Unable to fetch data for {ticker}. Please try another stock.</p>"

    # Generate and save the data to a JSON file
    json_filename, combined_data = save_to_json(ticker, data)
    
    # Display the stock data table
    stock_data_html = data.to_html(classes='table table-bordered', index=True)

    # JSON data for clipboard (stringified version)
    json_data_str = json.dumps(combined_data, indent=4)

    # Provide a link to download the JSON file
    download_link = f'<a href="/download/{json_filename}" class="btn btn-success">Download JSON</a>'
    
    return render_template('index.html', tickers=nifty_50_tickers, data=stock_data_html, download_link=download_link, json_data=json_data_str)

# Route to download the JSON file
@app.route('/download/<filename>')
def download(filename):
    return send_file(filename, as_attachment=True)

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
