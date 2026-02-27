import os
import requests
import yfinance as yf
import time
from datetime import datetime
import pytz

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# قائمة أولية كبيرة (نقدر نوسعها لاحقاً)
symbols = yf.Tickers(" ".join(yf.shared._EXCHANGE_TO_SYMBOLS.get("NMS", []))).symbols

alerted_levels = {}

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def is_market_open():
    tz = pytz.timezone("US/Eastern")
    now = datetime.now(tz)
    return now.weekday() < 5

def check_momentum():
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", interval="1m")

            if len(hist) < 2:
                continue

            open_price = hist["Close"].iloc[0]
            current_price = hist["Close"].iloc[-1]

            # فلتر السعر
            if current_price < 0.05 or current_price > 5:
                continue

            # فلتر فوليوم (آخر 5 دقائق)
            vol_5m = hist["Volume"].iloc[-5:].sum()
            if vol_5m < 50000:
                continue

            change = ((current_price - open_price) / open_price) * 100

            if change >= 2.5:
                level = round((change - 2.5) // 0.5 * 0.5 + 2.5, 2)
                last_level = alerted_levels.get(symbol)

                if last_level is None or level > last_level:
                    alerted_levels[symbol] = level

                    vol_1m = hist["Volume"].iloc[-1]
                    vol_2m = hist["Volume"].iloc[-2:].sum()

                    direction = "🟢 الاتجاه ← صاعد"

                    tz = pytz.timezone("US/Eastern")
                    now = datetime.now(tz).strftime("%I:%M:%S %p")

                    message = f"""🚀 MOMENTUM ALERT

🔶 {symbol} ← الرمز
🚨 اختراق مستوى {level:.2f}%
⚪ الإشارة ← زخم
{direction}

💰 السعر ← {current_price:.2f}$ (+{change:.2f}%)

📊 الفوليوم
1m: {vol_1m:,}
2m: {vol_2m:,}
5m: {vol_5m:,}

⏰ {now}
"""
                    send(message)

        except:
            continue

while True:
    if is_market_open():
        check_momentum()
    time.sleep(20)
