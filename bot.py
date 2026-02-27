import os
import requests
import yfinance as yf
import time
from datetime import datetime
import pytz
import random

# ==============================
# Telegram
# ==============================
TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

# ==============================
# Market Time Filter
# ==============================
def market_is_open():
    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    open_time = now.replace(hour=9, minute=30, second=0)
    close_time = now.replace(hour=16, minute=0, second=0)
    return open_time <= now <= close_time

# ==============================
# Settings
# ==============================
symbols = [
    "NVDA","TSLA","AAPL","AMD","META","AMZN","NFLX","SMCI","PLTR","COIN"
    # تقدر تزيد حتى 900 شركة
]

MIN_VOLUME = 100
ALERT_STEP = 10  # كل 10% حركة
TARGET_PERCENT = 50  # الهدف +50% من السعر عند أول تنبيه
BATCH_SIZE = 50

alerted_levels = {}  # السعر قبل كل تنبيه
strike_prices = {}   # Strike لكل عقد
targets = {}         # هدف العقد لكل عقد

# ==============================
# Scanner
# ==============================
while True:
    try:
        if not market_is_open():
            print("Market Closed")
            time.sleep(60)
            continue

        batch_symbols = random.sample(symbols, min(BATCH_SIZE, len(symbols)))

        for symbol in batch_symbols:
            stock = yf.Ticker(symbol)
            expirations = stock.options
            if not expirations:
                continue

            for nearest_exp in expirations:
                chain = stock.option_chain(nearest_exp)

                for opt_type, df in [("CALL", chain.calls), ("PUT", chain.puts)]:
                    for _, row in df.iterrows():
                        strike = row["strike"]
                        last_price = row["lastPrice"]
                        volume = row["volume"]

                        if last_price is None or volume is None:
                            continue
                        if volume < MIN_VOLUME:
                            continue

                        contract_id = f"{symbol}-{opt_type}-{strike}-{nearest_exp}"

                        # أول مرة يشوف العقد
                        if contract_id not in alerted_levels:
                            alerted_levels[contract_id] = last_price
                            strike_prices[contract_id] = strike
                            targets[contract_id] = last_price * (1 + TARGET_PERCENT/100)
                            continue

                        base_price = alerted_levels[contract_id]
                        percent_change = ((last_price - base_price) / base_price) * 100

                        if percent_change >= ALERT_STEP:
                            target_price = targets[contract_id]
                            message = f"""
🚀 {ALERT_STEP}% MOVE ALERT

🔸 الرمز -> {symbol}
🟢 {opt_type}

📅 Exp -> {nearest_exp}
📌 Strike -> {strike_prices[contract_id]}

💰 Before Move -> {base_price:.2f}$
📍 After Move -> {last_price:.2f}$
📈 Change -> +{percent_change:.2f}%
🎯 Target -> {target_price:.2f}$

📊 Volume -> {int(volume):,}
"""
                            send_telegram(message)
                            # تحديث السعر قبل التنبيه القادم
                            alerted_levels[contract_id] = last_price

        time.sleep(60)

    except Exception as e:
        print("Error:", e)
        time.sleep(30)
