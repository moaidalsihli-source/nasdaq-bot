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

SEND_DELAY = 5
MAX_PRICE = 10

sent_symbols = set()

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

print("Momentum Sniper Bot Started 🔥")

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

            # فلتر أقل من 10$
            if price >= MAX_PRICE:
                continue

            df['VWAP'] = calculate_vwap(df)
            df['RSI'] = calculate_rsi(df)

            # قمة أول 15 دقيقة
            opening_high = df['High'].iloc[0:3].max()

            # Volume Spike
            last_vol = df['Volume'].iloc[-1]
            avg_last5 = df['Volume'].iloc[-6:-1].mean()
            volume_spike = last_vol > avg_last5 * 3

            # RVOL
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
                qualified.append((symbol, price, df, rvol))

        except:
            continue

    random.shuffle(qualified)

    for symbol, price, df, rvol in qualified:

        if symbol in sent_symbols:
            continue

        vwap = df['VWAP'].iloc[-1]
        rsi = df['RSI'].iloc[-1]
        stop_loss = round(vwap * 0.995, 2)
        target1 = round(price * 1.015, 2)
        target2 = round(price * 1.02, 2)

        message = f"""
━━━━━━━━━━━━━━━━━━
⚡ تنبيه اختراق زخم قوي

الرمز: {symbol}
النموذج: اختراق نطاق الافتتاح (5 دقائق)

السعر الحالي: {round(price,2)}$
VWAP: {round(vwap,2)}$ (الثبات أعلى المتوسط المؤسسي)
RSI: {round(rsi,1)} (منطقة قوة شرائية)
الحجم النسبي RVOL: {round(rvol,2)}x
انفجار سيولة 5د: ✔

منطقة الدخول: إغلاق فوق قمة الافتتاح
وقف الخسارة: {stop_loss}$ (أسفل VWAP بـ 0.5%)
الهدف الأول: {target1}$
الهدف الثاني: {target2}$

نوع الحركة: زخم سهم خفيف (Low Float)
السعر أقل من 10$ ✔
━━━━━━━━━━━━━━━━━━
"""

        send_telegram(message)
        sent_symbols.add(symbol)

        time.sleep(SEND_DELAY)

    time.sleep(3)
