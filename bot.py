import requests
import yfinance as yf
import time
import os
import pytz
from datetime import datetime, time as dtime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

EST = pytz.timezone("US/Eastern")

def is_trading_session():
    now = datetime.now(EST).time()
    pre_start = dtime(4, 0)
    market_open = dtime(9, 30)
    market_close = dtime(16, 0)
    return (pre_start <= now < market_open) or (market_open <= now <= market_close)

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, data=payload)

def check_stocks():
    tickers = ["AAPL", "TSLA", "AMD", "NVDA", "PLTR"]
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d", interval="1m")
        if not data.empty:
            price = data["Close"].iloc[-1]
            volume = data["Volume"].iloc[-1]

            if price >= 100:
                message = f"🚀 {ticker}\nPrice: ${price}\nVolume: {volume}"
                send_message(message)

while True:
    if is_trading_session():
        check_stocks()
    time.sleep(60)
