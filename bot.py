import yfinance as yf
import requests
import time
import os
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

MIN_PRICE = 0.07
MAX_PRICE = 20
CHANGE_THRESHOLD = 3  # %
REQUEST_DELAY = 1     # 1 second between requests

sent_alerts = {}

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except:
        pass

def get_sp500_symbols():
    table = yf.download("^GSPC", period="1d")
    # fallback list بسيط
    return ["AAPL","TSLA","SOFI","NVDA","AMD","PLTR","F"]

def scan_market():
    symbols = get_sp500_symbols()

    for symbol in symbols:
        try:
            data = yf.download(symbol, period="2d", interval="1m", progress=False)

            if data.empty or len(data) < 2:
                continue

            current_price = float(data["Close"].iloc[-1])
            prev_close = float(data["Close"].iloc[-2])

            if current_price < MIN_PRICE or current_price > MAX_PRICE:
                continue

            change_percent = ((current_price - prev_close) / prev_close) * 100

            if abs(change_percent) >= CHANGE_THRESHOLD:

                if symbol in sent_alerts:
                    last_price = sent_alerts[symbol]
                    if abs(current_price - last_price) < 0.01:
                        continue

                sent_alerts[symbol] = current_price

                direction = "🟢 UP" if change_percent > 0 else "🔴 DOWN"

                message = f"""
🚨 <b>STOCK ALERT</b>

📌 {symbol}
💲 Price: {current_price:.2f}
📊 Change: {change_percent:.2f}%
{direction}

🕒 {datetime.now().strftime('%H:%M:%S')}
"""
                send_message(message)

            time.sleep(REQUEST_DELAY)

        except Exception as e:
            print("Error:", e)
            continue

if __name__ == "__main__":
    print("🚀 BOT STARTED")

    while True:
        try:
            scan_market()
        except Exception as e:
            print("Main Loop Error:", e)

        time.sleep(1)
