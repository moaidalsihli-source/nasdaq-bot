import os
import requests
import yfinance as yf
import pandas as pd
import pytz
import time
from datetime import datetime

# =============================
# قراءة متغيرات Railway
# =============================

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not TOKEN or not CHAT_ID:
    print("❌ TOKEN OR CHAT_ID NOT FOUND!")
    exit()

# =============================
# إعدادات
# =============================

ny = pytz.timezone("America/New_York")

stock_levels = {}
option_levels = {}

# =============================
# وقت السوق الرسمي للعقود
# =============================

def market_is_open():
    now = datetime.now(ny)

    if now.weekday() >= 5:
        return False

    current_minutes = now.hour * 60 + now.minute
    open_minutes = 9 * 60 + 30
    close_minutes = 16 * 60

    return open_minutes <= current_minutes <= close_minutes

# =============================
# تحميل أسهم NASDAQ
# =============================

def get_nasdaq():
    url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
    df = pd.read_csv(url, sep="|")
    tickers = df["Symbol"].tolist()
    return [t for t in tickers if isinstance(t, str)]

print("Loading NASDAQ...")
all_tickers = get_nasdaq()
print("Loaded:", len(all_tickers))

# =============================
# إرسال رسالة
# =============================

def send_message(text):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text}
    )

# =============================
# رسالة بدء التشغيل
# =============================

def send_startup_message():
    now_ny = datetime.now(ny).strftime("%I:%M:%S %p")

    message = f"""
🚀 NASDAQ SCANNER STARTED

📊 Stocks: 3% then every +3%
📑 Options: 25% then every +10%
📡 Options Active: Official Market Only

🕒 Started At: {now_ny} NY
"""
    send_message(message)

send_startup_message()

# =============================
# تنبيه السهم (كل +3%)
# =============================

def check_stock_levels(ticker, price, change, accel):

    if ticker not in stock_levels:
        stock_levels[ticker] = 0

    last_level = stock_levels[ticker]
    abs_change = abs(change)

    if last_level == 0 and abs_change >= 3:
        level_hit = 3
    elif last_level >= 3:
        next_level = last_level + 3
        if abs_change >= next_level:
            level_hit = next_level
        else:
            return
    else:
        return

    stock_levels[ticker] = level_hit

    direction = "🟢" if change > 0 else "🔴"
    header = "STOCK BREAKOUT" if change > 0 else "STOCK BREAKDOWN"
    now_ny = datetime.now(ny).strftime("%I:%M:%S %p")

    message = f"""
🔸 {ticker}
{direction} {header}

💰 Price: {round(price,2)}$
📊 Move: {round(change,2)}%
🎯 Level Hit: {level_hit}%

⚡ 3m Acceleration: {round(accel,2)}
🕒 {now_ny} NY
"""
    send_message(message)

# =============================
# تنبيه العقد (25% ثم +10%)
# =============================

def check_option_levels(ticker, exp, strike, current_price, volume, direction):

    key = f"{ticker}_{strike}_{exp}"

    if key not in option_levels:
        option_levels[key] = {
            "entry": current_price,
            "last_level": 0
        }
        return

    entry = option_levels[key]["entry"]
    last_level = option_levels[key]["last_level"]

    change = ((current_price - entry) / entry) * 100

    if last_level == 0 and change >= 25:
        level_hit = 25
    elif last_level >= 25:
        next_level = last_level + 10
        if change >= next_level:
            level_hit = next_level
        else:
            return
    else:
        return

    option_levels[key]["last_level"] = level_hit

    color = "🟢 CALL" if direction == "CALL" else "🔴 PUT"
    now_ny = datetime.now(ny).strftime("%I:%M:%S %p")

    message = f"""
🔸 {ticker}
{color} OPTION LEVEL

📅 Exp: {exp}
📌 Strike: {strike}
💲 Entry: {round(entry,2)}
💲 Current: {round(current_price,2)}
🚀 +{level_hit}%

🔥 Volume: {int(volume)}
🕒 {now_ny} NY
"""
    send_message(message)

# =============================
# التشغيل الرئيسي
# =============================

while True:

    for ticker in all_tickers[:250]:

        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="1d", interval="1m")

            if len(data) < 5:
                continue

            price = data["Close"].iloc[-1]
            open_price = data["Open"].iloc[0]
            change = ((price - open_price) / open_price) * 100
            accel = ((price - data["Close"].iloc[-4]) / data["Close"].iloc[-4]) * 100

            if 0.07 <= price <= 10:
                check_stock_levels(ticker, price, change, accel)

                if market_is_open():
                    direction = "CALL" if change > 0 else "PUT"

                    for exp in stock.options:
                        chain = stock.option_chain(exp)
                        options = chain.calls if direction=="CALL" else chain.puts

                        for _, row in options.iterrows():

                            opt_price = row["lastPrice"]
                            strike = row["strike"]
                            vol = row["volume"]

                            if pd.isna(opt_price) or pd.isna(vol):
                                continue

                            if 0.05 <= opt_price <= 0.50:
                                check_option_levels(
                                    ticker, exp, strike,
                                    opt_price, vol, direction
                                )

        except:
            continue

        time.sleep(0.3)

    time.sleep(5)
