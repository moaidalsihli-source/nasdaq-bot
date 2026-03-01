import os
import requests
import yfinance as yf
import time
from datetime import datetime, time as dt_time
import pytz
import pandas as pd
import random

# ==============================
# إعداد تيليجرام للقناة
# ==============================
TOKEN = os.environ.get("TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")  # مثال: @YourChannelUsername

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHANNEL_ID, "text": message})

# ==============================
# أوقات السوق
# ==============================
ny = pytz.timezone("America/New_York")
MARKET_OPEN = dt_time(9, 30)
MARKET_CLOSE = dt_time(16, 0)

def market_status_now():
    now = datetime.now(ny)
    current_time = now.time()
    weekday = now.weekday()

    if weekday >= 5:
        return "السوق مغلق اليوم 🔴"
    elif MARKET_OPEN <= current_time <= MARKET_CLOSE:
        return "السوق مفتوح الآن 🟢"
    elif current_time < MARKET_OPEN:
        return "السوق سيفتح قريبًا ⏰"
    else:
        return "السوق مغلق الآن 🔴"

# ==============================
# إرسال حالة السوق فور بدء البوت
# ==============================
send_telegram(f"🚀 البوت بدأ التشغيل ✅ | {market_status_now()}")

# ==============================
# إعداد الأسهم (يمكنك تكمل حتى 1000 سهم)
# ==============================
symbols = ["BATL","NIO","PLTR","AMC","GME","BB","NVDA","TSLA","AMD","AAPL"]
alert_count = {sym: 0 for sym in symbols}
alerted_prices = {}

# ==============================
# إعداد الفلتر
# ==============================
PRICE_MIN = 0.05
PRICE_MAX = 10.0
ALERT_STEP = 2.0
RSI_PERIOD = 14
EMA_PERIOD = 50
BATCH_SIZE = 50

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
# تشغيل المراقبة
# ==============================
while True:
    try:
        # تحقق حالة السوق كل دقيقة
        status = market_status_now()
        send_telegram(f"⏰ تحديث حالة السوق: {status}")

        batch_symbols = random.sample(symbols, min(BATCH_SIZE, len(symbols)))

        for symbol in batch_symbols:
            try:
                stock = yf.Ticker(symbol)
                data = stock.history(period="60d")['Close']
                volume_data = stock.history(period="5d", interval="1m")['Volume']

                if data.empty or volume_data.empty:
                    continue

                last_price = data.iloc[-1]
                if last_price < PRICE_MIN or last_price > PRICE_MAX:
                    continue

                ema50 = compute_ema(data, EMA_PERIOD).iloc[-1]
                rsi = compute_rsi(data, RSI_PERIOD).iloc[-1]

                # تحديد نوع الإشارة
                if last_price > ema50 and rsi > 55:
                    signal = "زخم"
                    direction = "🟢 صاعد"
                elif last_price > data.max():
                    signal = "قمة أعلى جديدة"
                    direction = "🟢 صاعد"
                else:
                    continue

                if symbol not in alerted_prices:
                    alerted_prices[symbol] = last_price
                    continue

                base_price = alerted_prices[symbol]
                percent_change = ((last_price - base_price) / base_price) * 100
                if percent_change < ALERT_STEP:
                    continue

                # فوليوم لفترات 1m, 2m, 5m
                vol_1m = volume_data.iloc[-1]
                vol_2m = volume_data.iloc[-2] if len(volume_data) > 1 else vol_1m
                vol_5m = volume_data.iloc[-5] if len(volume_data) > 4 else vol_1m

                alerted_prices[symbol] = last_price
                alert_count[symbol] += 1
                alert_number = alert_count[symbol]

                message = f"""
RadarMom

🔸 الرمز -> {symbol}
🚨 تنبيه رقم {alert_number} اليوم
⚪️ الإشارة -> {signal} | {direction}
💰 السعر -> {last_price:.2f}$ (+{percent_change:.1f}%)
📊 الفوليوم -> 1m: {int(vol_1m/1000):,}K | 2m: {int(vol_2m/1000):,}K | 5m: {int(vol_5m/1000):,}K
"""
                send_telegram(message)

            except Exception as e:
                print(f"خطأ في السهم {symbol}: {e}")
                continue

        time.sleep(60)  # تحقق كل دقيقة

    except Exception as e:
        print("خطأ عام:", e)
        time.sleep(30)
