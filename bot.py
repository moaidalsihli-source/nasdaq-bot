import os
import time
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# =============================
# إعدادات تيليجرام
# =============================

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not TOKEN or not CHAT_ID:
    print("❌ ضع TOKEN و CHAT_ID في Railway")
    exit()

# =============================
# إعدادات البوت
# =============================

CHECK_INTERVAL = 60
PERCENT_TRIGGER = 2.5
MAX_PRICE = 10
MIN_VOLUME = 200000
TOP_PER_CYCLE = 5

alert_counter = 0
sent_today = set()

# =============================
# إيقاف السبت والأحد
# =============================

def weekend_stop():
    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)
    return now.weekday() >= 5

# =============================
# جلب الأسهم الأكثر تداولاً فقط
# =============================

def get_active_stocks():
    tickers = yf.Tickers("^IXIC")
    return ["AAPL","TSLA","NVDA","AMD","SOFI","LCID","PLTR","NIO","RIVN","INTC","META","AMZN"]

# =============================
# إرسال رسالة
# =============================

def send_alert(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    requests.post(url, data=payload)

# =============================
# فحص السوق
# =============================

def scan_market():
    global alert_counter

    symbols = get_active_stocks()
    candidates = []

    for symbol in symbols:
        try:
            stock = yf.Ticker(symbol)
            data = stock.history(period="1d", interval="1m")

            if data.empty:
                continue

            price = data["Close"].iloc[-1]
            open_price = data["Open"].iloc[0]
            percent = ((price - open_price) / open_price) * 100

            if price > MAX_PRICE:
                continue

            if percent < PERCENT_TRIGGER:
                continue

            total_volume = data["Volume"].sum()
            if total_volume < MIN_VOLUME:
                continue

            if symbol in sent_today:
                continue

            vol_1m = data["Volume"].iloc[-1]
            vol_2m = data["Volume"].tail(2).sum()
            vol_5m = data["Volume"].tail(5).sum()

            candidates.append((symbol, percent, price, vol_1m, vol_2m, vol_5m))

        except:
            continue

    candidates.sort(key=lambda x: x[1], reverse=True)
    top = candidates[:TOP_PER_CYCLE]

    if not top:
        return

    message = "🚨 NASDAQ FAST RADAR 🚨\n\n"

    for sym, pct, price, v1, v2, v5 in top:
        alert_counter += 1
        sent_today.add(sym)

        message += f"""{sym} ◀ الرمز
🚨 تنبيه {alert_counter}

🟢 صعود قوي
💰 ${price:.2f} (+{pct:.1f}%)

📊 1m: {v1:,} | 2m: {v2:,} | 5m: {v5:,}

------------------

"""

    send_alert(message)

# =============================
# تشغيل مستمر
# =============================

print("🚀 NASDAQ FAST Radar Started")

while True:

    if weekend_stop():
        print("⏸ ويكند - متوقف")
        time.sleep(600)
        continue

    scan_market()
    time.sleep(CHECK_INTERVAL)
