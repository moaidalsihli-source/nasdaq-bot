import os
import requests
import yfinance as yf
import time
from datetime import datetime
import pytz
import random
import math

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
    if now.weekday() >= 5:  # السبت والأحد
        return False
    open_time = now.replace(hour=9, minute=30, second=0)
    close_time = now.replace(hour=16, minute=0, second=0)
    return open_time <= now <= close_time

# ==============================
# Settings
# ==============================
symbols = [
    "NVDA","TSLA","AAPL","AMD","META","AMZN","NFLX","SMCI","PLTR","COIN"
    # أضف باقي الشركات حتى تصل 900+
]

MIN_VOLUME = 100
ALERT_STEP = 10    # تنبيه كل +10% حركة
TARGET_PERCENT = 50  # هدف العقد +50% من السعر عند أول تنبيه
BATCH_SIZE = 50    # عدد الشركات لكل دورة

alerted_levels = {}   # يخزن السعر قبل كل تنبيه لكل عقد
strike_prices = {}    # يخزن Strike لكل عقد
targets = {}          # يخزن Target Price لكل عقد

# ==============================
# Scanner
# ==============================
while True:
    try:
        if not market_is_open():
            print("Market Closed")
            time.sleep(60)
            continue

        # اختيار دفعة من الشركات لكل دورة
        batch_symbols = random.sample(symbols, min(BATCH_SIZE, len(symbols)))

        for symbol in batch_symbols:
            stock = yf.Ticker(symbol)
            expirations = stock.options
            if not expirations:
                continue

            for nearest_exp in expirations:
                try:
                    chain = stock.option_chain(nearest_exp)
                except Exception as e:
                    print(f"Failed to fetch option chain for {symbol} {nearest_exp}: {e}")
                    continue

                for opt_type, df in [("CALL", chain.calls), ("PUT", chain.puts)]:
                    for _, row in df.iterrows():
                        strike = row.get("strike")
                        last_price = row.get("lastPrice")
                        volume = row.get("volume")

                        # تجاهل البيانات غير صالحة
                        if last_price is None or strike is None or volume is None:
                            continue
                        if last_price <= 0 or volume < MIN_VOLUME:
                            continue

                        contract_id = f"{symbol}-{opt_type}-{strike}-{nearest_exp}"

                        # أول مرة يشوف العقد
                        if contract_id not in alerted_levels:
                            alerted_levels[contract_id] = last_price
                            strike_prices[contract_id] = strike
                            targets[contract_id] = last_price * (1 + TARGET_PERCENT/100)
                            continue

                        base_price = alerted_levels[contract_id]

                        # حماية من القسمة على صفر
                        if base_price <= 0:
                            continue

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
                            alerted_levels[contract_id] = last_price  # تحديث السعر قبل التنبيه القادم

        time.sleep(60)  # يفحص كل دقيقة دفعة جديدة

    except Exception as e:
        print("Error:", e)
        time.sleep(30)
