import os
import requests
import yfinance as yf
import pandas as pd
import pytz
import time
from datetime import datetime

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=data)

ny = pytz.timezone("America/New_York")

tickers = pd.read_csv(
    "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"
)["Symbol"].tolist()

index = 0

def get_session_label(now):
    if 4 <= now.hour < 9 or (now.hour == 9 and now.minute < 30):
        return "🔵 Pre-Market"
    elif (now.hour > 9 or (now.hour == 9 and now.minute >= 30)) and now.hour < 16:
        return "🟢 Official Market"
    elif 16 <= now.hour < 20:
        return "🟣 After-Market"
    else:
        return "🌙 Extended Hours"

def check_stock(ticker, now):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d", interval="1m")

        if len(data) < 30:
            return None

        price = data["Close"].iloc[-1]
        open_price = data["Open"].iloc[0]

        # فلترة السعر
        if not (0.5 <= price <= 10):
            return None

        # ======================
        # الشروط الأساسية
        # ======================

        # 1️⃣ كسر أعلى 20 دقيقة
        high_20 = data["High"].tail(20).max()
        bos = price >= high_20

        # 2️⃣ فوليوم قوي جدًا
        avg_vol = data["Volume"].tail(20).mean()
        current_vol = data["Volume"].iloc[-1]
        volume_strong = current_vol >= avg_vol * 2.5

        if not (bos and volume_strong):
            return None

        # ======================
        # الشروط الداعمة
        # ======================

        support_score = 0

        # ارتداد من القاع
        day_low = data["Low"].min()
        rebound_percent = ((price - day_low) / day_low) * 100
        if rebound_percent >= 3:
            support_score += 1

        # تسارع 5 دقائق
        price_5m_ago = data["Close"].iloc[-6]
        accel_percent = ((price - price_5m_ago) / price_5m_ago) * 100
        if accel_percent >= 2.5:
            support_score += 1

        # حركة يومية
        day_change = ((price - open_price) / open_price) * 100
        if abs(day_change) >= 4:
            support_score += 1

        if support_score < 1:
            return None

        direction = "🟢 صعود" if day_change > 0 else "🔴 هبوط"
        session = get_session_label(now)

        message = (
            f"\n👑 Elite Aggressive Scanner\n"
            f"{session}\n"
            f"🔸 {ticker}\n"
            f"{direction}\n"
            f"💰 السعر: {round(price,2)}$\n"
            f"📊 حركة يومية: {round(day_change,2)}%\n"
            f"📈 ارتداد من القاع: {round(rebound_percent,2)}%\n"
            f"⚡ تسارع 5 دقائق: {round(accel_percent,2)}%\n"
            f"🔥 الفوليوم الحالي: {int(current_vol)}"
        )

        return message

    except:
        return None


send_message("👑 Elite Aggressive Scanner بدأ الآن")

while True:
    now = datetime.now(ny)

    if index >= len(tickers):
        index = 0

    ticker = tickers[index]
    index += 1

    msg = check_stock(ticker, now)

    if msg:
        send_message(msg)
        time.sleep(20)
    else:
        time.sleep(0.8)
