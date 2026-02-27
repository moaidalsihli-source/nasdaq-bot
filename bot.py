import os
import requests
import yfinance as yf
import time
from datetime import datetime
import pytz
import random

# ==============================
# إعدادات تيليجرام
# ==============================
TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

# ==============================
# التحقق من وقت السوق
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
# الإعدادات
# ==============================
symbols = [
    "NVDA","TSLA","AAPL","AMD","META","AMZN","NFLX","SMCI","PLTR","COIN"
    # أضف باقي الشركات هنا
]

MIN_VOLUME = 100
ALERT_STEP = 10        # تنبيه كل 10%
TARGET_PERCENT = 50    # الهدف 50%
BATCH_SIZE = 50

alerted_levels = {}
strike_prices = {}
targets = {}

# ==============================
# التشغيل
# ==============================
while True:
    try:
        if not market_is_open():
            print("السوق مغلق حالياً")
            time.sleep(60)
            continue

        batch_symbols = random.sample(symbols, min(BATCH_SIZE, len(symbols)))

        for symbol in batch_symbols:
            stock = yf.Ticker(symbol)
            expirations = stock.options
            if not expirations:
                continue

            for nearest_exp in expirations:
                try:
                    chain = stock.option_chain(nearest_exp)
                except:
                    continue

                for opt_type, df in [("CALL", chain.calls), ("PUT", chain.puts)]:
                    for _, row in df.iterrows():
                        strike = row.get("strike")
                        last_price = row.get("lastPrice")
                        volume = row.get("volume")

                        if last_price is None or strike is None or volume is None:
                            continue
                        if last_price <= 0 or volume < MIN_VOLUME:
                            continue

                        contract_id = f"{symbol}-{opt_type}-{strike}-{nearest_exp}"

                        if contract_id not in alerted_levels:
                            alerted_levels[contract_id] = last_price
                            strike_prices[contract_id] = strike
                            targets[contract_id] = last_price * (1 + TARGET_PERCENT/100)
                            continue

                        base_price = alerted_levels[contract_id]

                        if base_price <= 0:
                            continue

                        percent_change = ((last_price - base_price) / base_price) * 100

                        if percent_change >= ALERT_STEP:

                            direction = "🟢 عقد شراء (CALL)" if opt_type == "CALL" else "🔴 عقد بيع (PUT)"

                            message = f"""
🚀 تنبيه حركة قوية في عقد أوبشن

🔹 السهم: {symbol}
📌 نوع العقد: {direction}
📅 تاريخ الانتهاء: {nearest_exp}
🎯 سعر التنفيذ (Strike): {strike_prices[contract_id]}

💰 السعر قبل الارتفاع: {base_price:.2f}$
📈 السعر الحالي: {last_price:.2f}$
📊 نسبة التغير: +{percent_change:.2f}%

🏁 هدف العقد: {targets[contract_id]:.2f}$

📦 حجم التداول: {int(volume):,}
"""

                            send_telegram(message)
                            alerted_levels[contract_id] = last_price

        time.sleep(60)

    except Exception as e:
        print("خطأ:", e)
        time.sleep(30)
