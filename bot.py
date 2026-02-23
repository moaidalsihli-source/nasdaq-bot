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

ALERT_INTERVAL = 25
last_alert_time = 0
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
# NASDAQ LIST (cleaned)
# =============================

def get_nasdaq():
    url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
    df = pd.read_csv(url, sep="|")
    df = df[df["Test Issue"] == "N"]
    df = df[df["ETF"] == "N"]

    # remove warrants / preferred / weird symbols
    df = df[~df["Symbol"].str.contains(r"\^|W$|R$|P$")]

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

        if data is None or data.empty:
            time.sleep(0.5)
            continue

        if len(data) < 6:
            time.sleep(0.5)
            continue

        price = float(data["Close"].iloc[-1])
        open_price = float(data["Open"].iloc[0])

        if open_price == 0:
            continue

        change = ((price - open_price) / open_price) * 100
        accel = ((price - float(data["Close"].iloc[-4])) / float(data["Close"].iloc[-4])) * 100

        vol_1m = int(data["Volume"].iloc[-1])
        vol_2m = int(data["Volume"].tail(2).sum())
        vol_5m = int(data["Volume"].tail(5).sum())

        # =============================
        # STOCK SIGNAL
        # =============================

        if 0.07 <= price <= 20 and abs(change) >= 3:

            if change >= 12:
                momentum = "🔥 Explosive"
            elif change >= 8:
                momentum = "🚀 Powerful Move"
            elif change >= 5:
                momentum = "🟢 Strong Momentum"
            elif change >= 3:
                momentum = "⚠️ Momentum"
            elif change <= -8:
                momentum = "💣 Heavy Selloff"
            else:
                momentum = "🔻 Bearish Pressure"

            direction = "🟢" if change > 0 else "🔴"
            header = "BREAKOUT" if change > 0 else "BREAKDOWN"

            message = f"""
🔸 {ticker}
{direction} STOCK {header}

💰 Price: {round(price,2)}$
📈 Move: {round(change,2)}%
⚡ 3m Accel: {round(accel,2)}%

📊 1m Vol: {vol_1m:,}
📊 2m Vol: {vol_2m:,}
📊 5m Vol: {vol_5m:,}

🎯 {momentum}
🕒 {datetime.now(ny).strftime("%I:%M:%S %p")} NY
"""
            send_message(message)

        # =============================
        # OPTIONS
        # =============================

        if market_is_open():

            stock = yf.Ticker(ticker)

            for exp in stock.options:

                chain = stock.option_chain(exp)

                for opt_type, df_opt in [("CALL", chain.calls), ("PUT", chain.puts)]:

                    for _, row in df_opt.iterrows():

                        strike = row["strike"]
                        last_price = row["lastPrice"]
                        volume = row["volume"]
                        oi = row["openInterest"]

                        if pd.isna(last_price):
                            continue
                        if not (0.05 <= float(last_price) <= 0.50):
                            continue
                        if strike > 100:
                            continue
                        if pd.isna(volume) or volume < 5000:
                            continue
                        if pd.isna(oi) or oi < 3000:
                            continue

                        key = f"{ticker}_{strike}_{exp}_{opt_type}"

                        if key not in option_levels:
                            option_levels[key] = float(last_price)
                            continue

                        entry = option_levels[key]
                        gain = ((float(last_price) - entry) / entry) * 100

                        if gain >= 25:

                            direction = "🟢" if opt_type == "CALL" else "🔴"

                            message = f"""
🔸 {ticker}
{direction} {opt_type} OPTION LEVEL HIT

📅 Exp: {exp}
📌 Strike: {strike}
💲 Entry: {round(entry,2)}
💲 Current: {round(float(last_price),2)}
🚀 +{round(gain,1)}%

🔥 Option Volume: {int(volume)}
🕒 {datetime.now(ny).strftime("%I:%M:%S %p")} NY
"""
                            send_message(message)
                            option_levels[key] = float(last_price)

    except Exception as e:
        print("Error:", e)

    time.sleep(1)
