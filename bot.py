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

INTERVAL = 30
MAX_ALERTS = 4
MIN_CHANGE = 2
MIN_VOLUME = 150000
MAX_PRICE = 20   # ✅ فقط الأسهم تحت 20$

alert_counter = 1
today_date = datetime.now().date()

# تحميل قائمة ناسداك
SYMBOLS = pd.read_csv(
    "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"
)["Symbol"].dropna().tolist()

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
    batch = SYMBOLS[:700]

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
            if len(df) < 6:
                continue

            current = df["Close"].iloc[-1]
            open_price = df["Open"].iloc[0]
            high_day = df["High"].max()

            change = ((current - open_price) / open_price) * 100
            total_volume = df["Volume"].sum()

            if (
                abs(change) >= MIN_CHANGE and
                total_volume >= MIN_VOLUME and
                current <= MAX_PRICE   # ✅ فلترة تحت 20$
            ):

                if current >= high_day:  # 🔥 هاي اليوم فقط

                    vol_1m = int(df["Volume"].iloc[-1])
                    vol_2m = int(df["Volume"].iloc[-2:].sum())
                    vol_5m = int(df["Volume"].iloc[-5:].sum())

                    movers.append((
                        symbol,
                        current,
                        change,
                        vol_1m,
                        vol_2m,
                        vol_5m
                    ))

        except:
            continue

    movers = sorted(movers, key=lambda x: abs(x[2]), reverse=True)
    return movers[:MAX_ALERTS]

while True:

    if datetime.now().date() != today_date:
        alert_counter = 1
        today_date = datetime.now().date()

    print("Scanning...")

    movers = scan_market()

    for symbol, price, change, v1, v2, v5 in movers:

        message = f"""
🔶 <b>{symbol}</b>

🚨 تنبيه رقم {alert_counter} اليوم

🔥 هاي جديد لليوم

💰 السعر ← ${round(price,2)} ({round(change,2)}%)

📊 الفوليوم
1m: {v1:,}
2m: {v2:,}
5m: {v5:,}
"""

        send_telegram(message)
        alert_counter += 1
        time.sleep(2)

    time.sleep(INTERVAL)
