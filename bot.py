import os
import requests
import yfinance as yf
import pandas as pd
import time
from datetime import datetime

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not TOKEN or not CHAT_ID:
    print("Missing TOKEN or CHAT_ID")
    exit()

INTERVAL = 60
MAX_ALERTS = 5
MIN_VOLUME = 200000
MIN_CHANGE = 2
MAX_PRICE = 20

# قائمة ضخمة (تقدر تضيف أكثر)
SYMBOLS = pd.read_csv(
    "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"
)["Symbol"].dropna().tolist()

sent_symbols = set()

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

def scan_market():
    movers = []

    batch = SYMBOLS[:800]  # نفحص أول 800 كل دورة (أمان ضد الحظر)

    data = yf.download(
        tickers=batch,
        period="1d",
        interval="1m",
        group_by="ticker",
        progress=False,
        threads=True
    )

    for symbol in batch:
        try:
            df = data[symbol]
            if len(df) < 5:
                continue

            current = df["Close"].iloc[-1]
            open_price = df["Open"].iloc[0]
            volume = df["Volume"].sum()

            change = ((current - open_price) / open_price) * 100

            if (
                abs(change) >= MIN_CHANGE
                and volume >= MIN_VOLUME
                and current <= MAX_PRICE
                and symbol not in sent_symbols
            ):
                movers.append((symbol, current, change, volume))

        except:
            continue

    movers = sorted(movers, key=lambda x: abs(x[2]), reverse=True)
    return movers[:MAX_ALERTS]

while True:
    print("Scanning market...")

    movers = scan_market()

    for symbol, price, change, volume in movers:
        direction = "🟢 صاعد" if change > 0 else "🔴 هابط"

        message = f"""
🔶 <b>{symbol}</b>

⚪️ الإشارة ← زخم قوي
📍 الاتجاه ← {direction}

💰 السعر ← ${round(price,2)} ({round(change,2)}%)

📊 حجم اليوم ← {int(volume):,}
"""

        send_telegram(message)
        sent_symbols.add(symbol)
        time.sleep(2)

    time.sleep(INTERVAL)
