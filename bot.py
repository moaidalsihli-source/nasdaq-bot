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

levels = [5, 10, 20, 50, 70, 100]

# تحميل قائمة ناسداك
tickers = pd.read_csv(
    "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"
)["Symbol"].tolist()

sent_today = set()
index = 0
weekend_notified = False

# ==============================
# تحديد نوع الجلسة (عرض فقط)
# ==============================

def get_session_label(now):
    if 4 <= now.hour < 9 or (now.hour == 9 and now.minute < 30):
        return "🔵 Pre-Market"
    elif (now.hour > 9 or (now.hour == 9 and now.minute >= 30)) and now.hour < 16:
        return "🟢 Official Market"
    elif 16 <= now.hour < 20:
        return "🟣 After-Market"
    else:
        return "⚫ Closed"

# ==============================
# فحص السيولة الاحترافي
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

        current_level = None
        for lvl in levels:
            if abs_change >= lvl:
                current_level = lvl

        if current_level is None:
            return None

        # ===== الفوليوم =====
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
            f"\n🚨 تنبيه سيولة احترافي\n"
            f"{session}\n"
            f"🔸 {ticker}\n"
            f"⚡️ مستوى {current_level}%+\n"
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
# الحلقة الرئيسية
# ==============================

while True:
    now = datetime.now(ny)

    # إذا سبت أو أحد
    if now.weekday() >= 5:
        if not weekend_notified:
            send_message("📴 السوق مغلق اليوم (عطلة نهاية الأسبوع)")
            weekend_notified = True
        time.sleep(3600)
        continue

    weekend_notified = False

    if index >= len(tickers):
        index = 0

    ticker = tickers[index]
    index += 1

    if ticker not in sent_today:
        msg = check_liquidity_stock(ticker, now)

        if msg:
            send_message(msg)
            sent_today.add(ticker)
            time.sleep(35)
