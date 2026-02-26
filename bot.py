import os
import requests
import yfinance as yf
import pandas as pd
import time
import random
from datetime import datetime

# =============================
# إعدادات تيليجرام
# =============================

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not TOKEN or not CHAT_ID:
    print("Missing TOKEN or CHAT_ID")
    exit()

# =============================
# إعدادات الفلترة
# =============================

INTERVAL = 30
MIN_CHANGE = 3          # نسبة التغير %
MIN_VOLUME = 150000     # أقل فوليوم
MAX_PRICE = 20          # أقصى سعر

# عداد مستقل لكل سهم
symbol_alert_counter = {}

# لمتابعة اليوم
today_date = datetime.now().date()

# =============================
# تحميل قائمة ناسداك كاملة
# =============================

SYMBOLS = pd.read_csv(
    "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"
)["Symbol"].dropna().tolist()

print(f"Loaded {len(SYMBOLS)} symbols")

# =============================
# إرسال تيليجرام
# =============================

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

# =============================
# تشغيل الرادار
# =============================

while True:

    # تصفير العدادات يومياً
    if datetime.now().date() != today_date:
        symbol_alert_counter.clear()
        today_date = datetime.now().date()
        print("Daily reset done")

    print("Scanning market...")

    # اختيار عشوائي عشان ما يتركز على A
    batch = random.sample(SYMBOLS, 700)

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
            change = ((current - open_price) / open_price) * 100
            total_volume = df["Volume"].sum()

            if (
                abs(change) >= MIN_CHANGE and
                total_volume >= MIN_VOLUME and
                current <= MAX_PRICE
            ):

                vol_1m = int(df["Volume"].iloc[-1])
                vol_2m = int(df["Volume"].iloc[-2:].sum())
                vol_5m = int(df["Volume"].iloc[-5:].sum())

                # عداد خاص لكل سهم
                if symbol not in symbol_alert_counter:
                    symbol_alert_counter[symbol] = 1
                else:
                    symbol_alert_counter[symbol] += 1

                direction = "🟢 صاعد" if change > 0 else "🔴 هابط"

                message = f"""
🔶 <b>{symbol}</b>

🚨 تنبيه رقم {symbol_alert_counter[symbol]} لهذا السهم

⚡ زخم قوي

📍 الاتجاه ← {direction}

💰 السعر ← ${round(current,2)} ({round(change,2)}%)

📊 الفوليوم
1m: {vol_1m:,}
2m: {vol_2m:,}
5m: {vol_5m:,}
"""

                send_telegram(message)
                time.sleep(1)

        except:
            continue

    time.sleep(INTERVAL)
