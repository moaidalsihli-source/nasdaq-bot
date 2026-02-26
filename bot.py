import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

MAX_PRICE = 20
SEND_DELAY = 5  # كل 5 ثواني

sent_symbols = set()  # منع التكرار بنفس الدورة

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
# قائمة الأسهم
# =============================

SYMBOLS = pd.read_csv(
    "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"
)["Symbol"].dropna().tolist()

while True:

    batch = random.sample(SYMBOLS, 150)

    data = yf.download(
        tickers=batch,
        period="2d",
        interval="5m",
        group_by="ticker",
        progress=False,
        threads=True
    )

    qualified = []

    for symbol in batch:
        try:
            df = data[symbol].dropna()
            if len(df) < 30:
                continue

            price = df['Close'].iloc[-1]
            if price > MAX_PRICE:
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
                price > df['VWAP'].iloc[-1] and
                60 < df['RSI'].iloc[-1] < 75 and
                volume_spike and
                rvol > 2 and
                df['Close'].iloc[-1] > opening_high
            ):
                qualified.append((symbol, price, df['VWAP'].iloc[-1]))

        except:
            continue

    random.shuffle(qualified)

    for symbol, price, vwap in qualified:

        if symbol in sent_symbols:
            continue

        stop_loss = round(vwap * 0.995, 2)
        take_profit = round(price * 1.02, 2)

        message = f"""
🎯 <b>{symbol}</b>

🚀 اختراق زخم مؤكد
📈 فوق VWAP
🔥 RVOL > 2
⚡ Volume Spike
📊 RSI 60-75
💥 اختراق أول 15 دقيقة

💰 السعر: {round(price,2)}
🛑 وقف: {stop_loss}
🎯 هدف: {take_profit}
"""

        send_telegram(message)
        sent_symbols.add(symbol)

        time.sleep(SEND_DELAY)

    time.sleep(3)
