import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np
import time
import random

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

SEND_DELAY = 5
MAX_PRICE = 10

tracked_symbols = {}

# =============================
# المؤشرات
# =============================

def calculate_vwap(df):
    q = df['Volume']
    p = (df['High'] + df['Low'] + df['Close']) / 3
    return (p * q).cumsum() / q.cumsum()

def calculate_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    })

# =============================
# تحميل قائمة ناسداك
# =============================

SYMBOLS = pd.read_csv(
    "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"
)["Symbol"].dropna().tolist()

print("Momentum Sniper Bot Running 🔥")

while True:

    batch = random.sample(SYMBOLS, 120)

    data = yf.download(
        tickers=batch,
        period="2d",
        interval="5m",
        group_by="ticker",
        progress=False,
        threads=True
    )

    # =============================
    # فحص الاختراق الأساسي
    # =============================

    for symbol in batch:
        try:
            df = data[symbol].dropna()
            if len(df) < 30:
                continue

            price = df['Close'].iloc[-1]

            # فلتر تحت 10$
            if price >= MAX_PRICE:
                continue

            df['VWAP'] = calculate_vwap(df)
            df['RSI'] = calculate_rsi(df)

            opening_high = df['High'].iloc[0:3].max()

            last_vol = df['Volume'].iloc[-1]
            avg_last5 = df['Volume'].iloc[-6:-1].mean()
            volume_spike = last_vol > avg_last5 * 3

            daily = yf.download(symbol, period="10d", interval="1d", progress=False)
            avg_vol_10d = daily['Volume'].mean()
            today_vol = df['Volume'].sum()
            rvol = today_vol / avg_vol_10d if avg_vol_10d > 0 else 0

            if (
                symbol not in tracked_symbols and
                price > df['VWAP'].iloc[-1] and
                60 < df['RSI'].iloc[-1] < 75 and
                volume_spike and
                rvol > 2 and
                df['Close'].iloc[-1] > opening_high
            ):

                tracked_symbols[symbol] = {
                    "entry_price": price,
                    "last_alert_price": price
                }

                vwap = df['VWAP'].iloc[-1]
                stop_loss = round(vwap * 0.995, 2)
                target1 = round(price * 1.015, 2)
                target2 = round(price * 1.02, 2)

                message = f"""
━━━━━━━━━━━━━━━━━━
⚡ تنبيه اختراق زخم قوي

الرمز: {symbol}
السعر: {round(price,2)}$

VWAP: {round(vwap,2)}
RSI: {round(df['RSI'].iloc[-1],1)}
RVOL: {round(rvol,2)}x

وقف: {stop_loss}$
هدف1: {target1}$
هدف2: {target2}$

سهم أقل من 10$ ✔
━━━━━━━━━━━━━━━━━━
"""
                send_telegram(message)
                time.sleep(SEND_DELAY)

        except:
            continue

    # =============================
    # تنبيهات الامتداد كل +3%
    # =============================

    for symbol in list(tracked_symbols.keys()):
        try:
            df_ext = yf.download(symbol, period="1d", interval="1m", progress=False)
            current_price = df_ext['Close'].iloc[-1]

            entry_price = tracked_symbols[symbol]["entry_price"]
            last_alert_price = tracked_symbols[symbol]["last_alert_price"]

            percent_move = ((current_price - last_alert_price) / last_alert_price) * 100

            if percent_move >= 3:

                total_move = ((current_price - entry_price) / entry_price) * 100

                message = f"""
━━━━━━━━━━━━━━━━━━
🚀 تنبيه امتداد زخم

الرمز: {symbol}
السعر الحالي: {round(current_price,2)}$

+{round(percent_move,2)}% من آخر تنبيه
إجمالي الحركة: +{round(total_move,2)}%

الزخم مستمر 🔥
━━━━━━━━━━━━━━━━━━
"""
                send_telegram(message)

                tracked_symbols[symbol]["last_alert_price"] = current_price

                time.sleep(SEND_DELAY)

        except:
            continue

    time.sleep(3)
