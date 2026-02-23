import os
import requests
import yfinance as yf
import pandas as pd
import pytz
import time
import random
from datetime import datetime

# =============================
# ENV
# =============================

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not TOKEN or not CHAT_ID:
    print("❌ TOKEN OR CHAT_ID NOT FOUND!")
    exit()

ny = pytz.timezone("America/New_York")

stock_levels = {}

# =============================
# ALERT CONTROL (45 SECONDS)
# =============================

last_alert_time = 0
ALERT_INTERVAL = 45  # seconds

# =============================
# MARKET TIME
# =============================

def market_is_open():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 570 <= minutes <= 960  # 9:30 - 16:00

# =============================
# CLEAN NASDAQ LIST
# =============================

def get_nasdaq():
    url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
    df = pd.read_csv(url, sep="|")

    df = df[df["Test Issue"] == "N"]
    df = df[df["ETF"] == "N"]
    df = df[df["NextShares"] == "N"]

    tickers = df["Symbol"].tolist()

    clean = []
    for t in tickers:
        if (
            isinstance(t, str)
            and "-" not in t
            and "." not in t
            and "^" not in t
            and "/" not in t
            and len(t) <= 5
        ):
            clean.append(t)

    return clean

print("Loading NASDAQ...")
all_tickers = get_nasdaq()
print("Clean symbols:", len(all_tickers))

# =============================
# TELEGRAM
# =============================

def send_message(text):
    global last_alert_time

    now = time.time()

    # يمنع الإرسال قبل مرور 45 ثانية
    if now - last_alert_time < ALERT_INTERVAL:
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": text
            }
        )

        last_alert_time = now

    except Exception as e:
        print("Telegram Error:", e)

# =============================
# STOCK CHECK
# =============================

def check_stock(ticker, price, change, accel):

    if ticker not in stock_levels:
        stock_levels[ticker] = 0

    last = stock_levels[ticker]
    abs_change = abs(change)

    if last == 0 and abs_change >= 3:
        level = 3
    elif last >= 3 and abs_change >= last + 3:
        level = last + 3
    else:
        return

    stock_levels[ticker] = level

    direction = "🟢" if change > 0 else "🔴"
    header = "BREAKOUT" if change > 0 else "BREAKDOWN"
    now_ny = datetime.now(ny).strftime("%I:%M:%S %p")

    message = f"""
🔸 {ticker}
{direction} STOCK {header}

💰 {round(price,2)}$
📊 {round(change,2)}%
🎯 Level {level}%
⚡ Accel {round(accel,2)}

🕒 {now_ny} NY
"""

    send_message(message)

# =============================
# MAIN LOOP (EVERY 30s SCAN)
# =============================

SCAN_INTERVAL = 30  # الفحص كل 30 ثانية

while True:

    cycle_start = time.time()

    # اختيار 200 سهم عشوائي لتخفيف الضغط
    sample = random.sample(all_tickers, 200)

    try:
        data = yf.download(
            tickers=" ".join(sample),
            period="1d",
            interval="1m",
            group_by="ticker",
            threads=True,
            progress=False
        )

        for ticker in sample:

            try:
                if ticker not in data:
                    continue

                df = data[ticker]

                if len(df) < 5:
                    continue

                price = df["Close"].iloc[-1]
                open_price = df["Open"].iloc[0]

                if open_price == 0:
                    continue

                change = ((price - open_price) / open_price) * 100
                accel = ((price - df["Close"].iloc[-4]) / df["Close"].iloc[-4]) * 100

                if 0.07 <= price <= 10:
                    check_stock(ticker, price, change, accel)

            except:
                continue

    except Exception as e:
        print("Download Error:", e)

    # ضبط توقيت 30 ثانية
    cycle_time = time.time() - cycle_start
    sleep_time = SCAN_INTERVAL - cycle_time

    if sleep_time > 0:
        time.sleep(sleep_time)
