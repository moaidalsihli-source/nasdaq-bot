import os
import requests
import yfinance as yf
import time
import pytz
import logging
from datetime import datetime

# ====== إيقاف رسائل yfinance ======
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

MIN_PRICE = 0.06
MAX_PRICE = 10
STEP = 3
BATCH_SIZE = 120
MIN_5M_VOLUME = 100000

ny = pytz.timezone("America/New_York")
memory = {}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

def get_nasdaq_symbols():
    url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&exchange=nasdaq&download=true"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    data = r.json()
    rows = data["data"]["rows"]
    return [row["symbol"] for row in rows if len(row["symbol"]) == 4]

def scan_collect(symbol):
    try:
        data = yf.Ticker(symbol).history(period="1d", interval="1m")

        if data is None or data.empty:
            return None

        open_price = data["Open"].iloc[0]
        current_price = data["Close"].iloc[-1]

        if not (MIN_PRICE <= current_price <= MAX_PRICE):
            return None

        change = ((current_price - open_price) / open_price) * 100
        if abs(change) < STEP:
            return None

        level = int(abs(change) // STEP) * STEP

        if symbol not in memory:
            memory[symbol] = []

        if level in memory[symbol]:
            return None

        memory[symbol].append(level)

        vol_1m = int(data["Volume"].iloc[-1]) if len(data) >= 1 else 0
        vol_2m = int(data["Volume"].iloc[-2:].sum()) if len(data) >= 2 else 0
        vol_5m = int(data["Volume"].iloc[-5:].sum()) if len(data) >= 5 else 0

        if vol_5m < MIN_5M_VOLUME:
            return None

        direction_icon = "🟢 صاعد" if change > 0 else "🔴 هابط"
        now_time = datetime.now(ny).strftime("%I:%M:%S %p NY")

        message = f"""
Mod F-15

🔸 الرمز -> {symbol}
🚨 تنبيه مستوى {level}%
⚪️ الإشارة -> زخم
{direction_icon}

💰 بدأ من -> {open_price:.2f}$
📍 الآن -> {current_price:.2f}$
📈 نسبة التغير -> {change:+.2f}%

📊 1m Vol -> {vol_1m:,}
📊 2m Vol -> {vol_2m:,}
📊 5m Vol -> {vol_5m:,}

🕒 {now_time}
"""
        return message

    except:
        return None

def main():
    now_time = datetime.now(ny).strftime("%I:%M:%S %p NY")
    send_telegram(f"🚀 BOT STARTED NOW\n🕒 {now_time}")

    symbols = get_nasdaq_symbols()
    index = 0

    while True:

        batch = symbols[index:index+BATCH_SIZE]

        for s in batch:
            message = scan_collect(s)
            if message:
                send_telegram(message)

        index += BATCH_SIZE
        if index >= len(symbols):
            index = 0

        time.sleep(10)

if __name__ == "__main__":
    main()
