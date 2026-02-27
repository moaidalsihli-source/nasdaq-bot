import os
import requests
import yfinance as yf
import time
import random
from datetime import datetime
import pytz

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
# ضع هنا قائمة 900 شركة (كمثال وضعت بعض الشركات)
symbols = [
    "AAPL","MSFT","AMZN","TSLA","NVDA","GOOGL","META","BRK-B","JNJ","V",
    # … تابع القائمة حتى تصل 900 شركة
]

MIN_VOLUME = 100
ALERT_STEP = 10  # كل 10% حركة
BATCH_SIZE = 50  # عدد الشركات لكل دورة (يمكن تعديله حسب سرعة السيرفر)

alerted_levels = {}  # آخر سعر تنبيه لكل عقد

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

                        if contract_id not in alerted_levels:
                            alerted_levels[contract_id] = last_price
                            continue

                        base_price = alerted_levels[contract_id]
                        percent_change = ((last_price - base_price) / base_price) * 100

                        if percent_change >= ALERT_STEP:
                            message = f"""
🚀 10% MOVE ALERT

🔸 الرمز -> {symbol}
🟢 {opt_type}

📅 Exp -> {nearest_exp}
📌 Strike -> {strike}

💰 Previous -> {base_price:.2f}$
📍 Now -> {last_price:.2f}$
📈 Change -> +{percent_change:.2f}%

📊 Volume -> {int(volume):,}
"""
                            send_telegram(message)
                            alerted_levels[contract_id] = last_price

        time.sleep(60)  # يفحص كل دقيقة دفعة جديدة

    except Exception as e:
        print("Error:", e)
        time.sleep(30)
