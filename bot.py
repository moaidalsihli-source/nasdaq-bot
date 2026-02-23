import os
import requests
import yfinance as yf
import pandas as pd
import pytz
import time
from datetime import datetime

# ==============================
# إعدادات البوت
# ==============================

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=data)

ny = pytz.timezone("America/New_York")

# تحميل قائمة ناسداك
tickers = pd.read_csv(
    "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"
)["Symbol"].tolist()

index = 0

# ==============================
# تحديد نوع الجلسة
# ==============================

def get_session_label(now):
    if 4 <= now.hour < 9 or (now.hour == 9 and now.minute < 30):
        return "🔵 Pre-Market"
    elif (now.hour > 9 or (now.hour == 9 and now.minute >= 30)) and now.hour < 16:
        return "🟢 Official Market"
    elif 16 <= now.hour < 20:
        return "🟣 After-Market"
    else:
        return "🌙 Extended Hours"

# ==============================
# فحص السيولة (3% وفوق)
# ==============================

def check_liquidity_stock(ticker, now):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d", interval="1m")

        if len(data) < 10:
            return None

        price = data["Close"].iloc[-1]
        open_price = data["Open"].iloc[0]

        if not (0.06 <= price <= 10):
            return None

        change_percent = ((price - open_price) / open_price) * 100
        abs_change = abs(change_percent)

        # شرط 3% وفوق
        if abs_change < 3:
            return None

        # الفوليوم
        vol_1m = data["Volume"].iloc[0]
        vol_2m = data["Volume"].iloc[:2].sum()
        vol_5m = data["Volume"].iloc[:5].sum()

        avg_vol = data["Volume"].tail(20).mean()
        current_vol = data["Volume"].iloc[-1]

        if vol_1m < 20000:
            return None

        if current_vol < avg_vol * 2:
            return None

        direction = "🟢 صعود" if change_percent > 0 else "🔴 هبوط"
        session = get_session_label(now)

        message = (
            f"\n🚨 تنبيه سيولة\n"
            f"{session}\n"
            f"🔸 {ticker}\n"
            f"{direction}\n"
            f"💰 السعر: {round(price,2)}$\n"
            f"📊 التغير: {round(change_percent,2)}%\n\n"
            f"🔥 فوليوم 1 دقيقة: {int(vol_1m)}\n"
            f"🔥 فوليوم 2 دقيقة: {int(vol_2m)}\n"
            f"🔥 فوليوم 5 دقائق: {int(vol_5m)}\n"
            f"📈 الفوليوم الحالي: {int(current_vol)}"
        )

        return message

    except:
        return None


# ==============================
# الحلقة الرئيسية (24 ساعة)
# ==============================

send_message("🚀 البوت بدأ — فلترة 3%+")

while True:
    now = datetime.now(ny)

    if index >= len(tickers):
        index = 0

    ticker = tickers[index]
    index += 1

    msg = check_liquidity_stock(ticker, now)

    if msg:
        send_message(msg)
        time.sleep(35)  # انتظار بعد التنبيه
    else:
        time.sleep(1)   # انتظار بسيط
