import os
import requests
import yfinance as yf
import pandas as pd
import pytz
import time
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

last_alert_time = 0
ALERT_INTERVAL = 30

stock_levels = {}
option_levels = {}

# =============================
# TELEGRAM
# =============================

def send_message(text):
    global last_alert_time

    now = time.time()
    if now - last_alert_time < ALERT_INTERVAL:
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text}
        )
        last_alert_time = now
    except Exception as e:
        print("Telegram Error:", e)

# =============================
# MARKET TIME
# =============================

def market_is_open():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 570 <= minutes <= 960  # 9:30 - 16:00 NY

# =============================
# NASDAQ LIST
# =============================

def get_nasdaq():
    url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
    df = pd.read_csv(url, sep="|")
    df = df[df["Test Issue"] == "N"]
    df = df[df["ETF"] == "N"]
    return df["Symbol"].tolist()

print("🚀 BOT STARTED NOW")
send_message("🚀 BOT STARTED NOW")

all_tickers = get_nasdaq()
ticker_index = 0

# =============================
# MAIN LOOP
# =============================

while True:

    ticker = all_tickers[ticker_index]
    ticker_index = (ticker_index + 1) % len(all_tickers)

    try:
        data = yf.download(ticker, period="1d", interval="1m", progress=False)

        if len(data) < 10:
            time.sleep(1)
            continue

        price = data["Close"].iloc[-1]
        open_price = data["Open"].iloc[0]
        change = ((price - open_price) / open_price) * 100
        accel = ((price - data["Close"].iloc[-4]) / data["Close"].iloc[-4]) * 100

        day_volume = data["Volume"].sum()
        vol_1m = data["Volume"].iloc[-1]
        vol_2m = data["Volume"].tail(2).sum()
        vol_5m = data["Volume"].tail(5).sum()

        # =============================
        # STOCK FILTER (0.03 - 1$)
        # =============================

        if 0.03 <= price <= 1 and day_volume >= 500000 and vol_5m >= 10000 and abs(accel) >= 1:

            level = int(abs(change) // 3) * 3
            if level >= 3:

                direction = "🟢" if change > 0 else "🔴"
                header = "BREAKOUT" if change > 0 else "BREAKDOWN"

                message = f"""
🔸 {ticker}
{direction} STOCK {header}

💰 Price: {round(price,3)}$
📈 Daily Change: {round(change,2)}%
⚡ 3m Accel: {round(accel,2)}%

📊 1m Vol: {vol_1m}
📊 2m Vol: {vol_2m}
📊 5m Vol: {vol_5m}

🎯 Level {level}%
🕒 {datetime.now(ny).strftime("%I:%M:%S %p")} NY
"""
                send_message(message)

        # =============================
        # OPTIONS (MARKET HOURS ONLY)
        # =============================

        if market_is_open():

            stock = yf.Ticker(ticker)

            for exp in stock.options:

                opt_chain = stock.option_chain(exp)

                for opt_type, df_opt in [("CALL", opt_chain.calls), ("PUT", opt_chain.puts)]:

                    for _, row in df_opt.iterrows():

                        strike = row["strike"]
                        last_price = row["lastPrice"]
                        volume = row["volume"]
                        oi = row["openInterest"]

                        if last_price is None:
                            continue

                        if not (0.05 <= last_price <= 0.50):
                            continue

                        if strike > 100:
                            continue

                        if volume is None or volume < 5000:
                            continue

                        if oi is None or oi < 3000:
                            continue

                        if volume < oi:
                            continue

                        if opt_type == "CALL" and change < 1:
                            continue

                        if opt_type == "PUT" and change > -1:
                            continue

                        key = f"{ticker}_{strike}_{exp}_{opt_type}"

                        if key not in option_levels:
                            option_levels[key] = last_price
                            continue

                        entry = option_levels[key]
                        gain = ((last_price - entry) / entry) * 100

                        if gain >= 25:

                            direction = "🟢" if opt_type == "CALL" else "🔴"

                            message = f"""
🔸 {ticker}
{direction} {opt_type} OPTION LEVEL HIT

📅 Exp: {exp}
📌 Strike: {strike}
💲 Entry: {round(entry,2)}
💲 Current: {round(last_price,2)}
🚀 +{round(gain,1)}%

🔥 Option Volume: {int(volume)}
🕒 {datetime.now(ny).strftime("%I:%M:%S %p")} NY
"""
                            send_message(message)
                            option_levels[key] = last_price

    except Exception as e:
        print("Error:", e)

    time.sleep(1)
