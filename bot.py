import os
import requests
import yfinance as yf
import time
from datetime import datetime
import pytz
import pandas as pd
import random

# ==============================
# إعداد تيليجرام
# ==============================
TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("خطأ في تيليجرام:", e)

# ==============================
# التحقق من وقت السوق
# ==============================
def market_is_open():
    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    open_time = now.replace(hour=9, minute=30, second=0)
    close_time = now.replace(hour=16, minute=0, second=0)
    return open_time <= now <= close_time

# ==============================
# إعداد الأسهم
# ==============================
# ضع هنا قائمة 1000 سهم أو أكثر
symbols = [
    "NIO","PLTR","AMC","SNDL","GME","BB","AAPL","NVDA","TSLA","AMD",
    # ... أكمل حتى 1000 سهم
]

MIN_VOLUME = 100_000
PRICE_MIN = 0.05
PRICE_MAX = 10.0
ALERT_STEP = 5
RSI_PERIOD = 14
EMA_PERIOD = 50
BATCH_SIZE = 50  # عدد الأسهم لكل دفعة

alerted_prices = {}

# ==============================
# دوال RSI و EMA
# ==============================
def compute_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_ema(prices, period=50):
    return prices.ewm(span=period, adjust=False).mean()

# ==============================
# حلقة المراقبة
# ==============================
while True:
    try:
        if not market_is_open():
            print("السوق مغلق حالياً")
            time.sleep(60)
            continue

        batch_symbols = random.sample(symbols, min(BATCH_SIZE, len(symbols)))

        alerts_this_batch = []

        for symbol in batch_symbols:
            try:
                stock = yf.Ticker(symbol)
                data = stock.history(period="60d")['Close']
                volume_data = stock.history(period="1d")['Volume']

                if data.empty or volume_data.empty:
                    continue

                last_price = data.iloc[-1]
                last_volume = volume_data.iloc[-1]

                if last_price < PRICE_MIN or last_price > PRICE_MAX:
                    continue
                if last_volume < MIN_VOLUME:
                    continue

                ema50 = compute_ema(data, EMA_PERIOD).iloc[-1]
                rsi = compute_rsi(data, RSI_PERIOD).iloc[-1]

                bullish = last_price > ema50 and rsi > 55
                bearish = last_price < ema50 and rsi < 45

                if symbol not in alerted_prices:
                    alerted_prices[symbol] = last_price
                    continue

                base_price = alerted_prices[symbol]
                percent_change = ((last_price - base_price) / base_price) * 100

                if bullish and percent_change >= ALERT_STEP:
                    direction = "🟢 صعود قوي"
                elif bearish and abs(percent_change) >= ALERT_STEP:
                    direction = "🔴 هبوط قوي"
                else:
                    continue

                message = f"""
{direction} في سهم

🔹 السهم: {symbol}
💰 السعر السابق: {base_price:.2f}$
📈 السعر الحالي: {last_price:.2f}$
📊 نسبة التغير: {percent_change:.2f}%
📊 RSI: {rsi:.2f}
📈 EMA50: {ema50:.2f}
📦 حجم التداول: {int(last_volume):,}
"""
                alerts_this_batch.append((percent_change, message))
                alerted_prices[symbol] = last_price

            except Exception as e:
                print(f"خطأ في السهم {symbol}: {e}")
                continue

        # إرسال التنبيهات مرتبة حسب أكبر نسبة تغير أولاً
        for _, msg in sorted(alerts_this_batch, key=lambda x: abs(x[0]), reverse=True):
            send_telegram(msg)

        time.sleep(60)

    except Exception as e:
        print("خطأ عام:", e)
        time.sleep(30)
