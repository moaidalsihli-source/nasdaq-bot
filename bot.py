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

stock_levels = {}
option_levels = {}

# =============================
# MARKET TIME
# =============================

def market_is_open():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 570 <= minutes <= 960  # 9:30 - 16:00

# =============================
# NASDAQ LIST
# =============================

def get_nasdaq():
    url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
    df = pd.read_csv(url, sep="|")

    df = df[(df["Test Issue"] == "N") &
            (df["ETF"] == "N") &
            (df["NextShares"] == "N")]

    tickers = df["Symbol"].tolist()

    clean = []
    for t in tickers:
        if isinstance(t, str) and len(t) <= 5 and "-" not in t and "." not in t:
            clean.append(t)

    return sorted(clean)

print("Loading NASDAQ...")
all_tickers = get_nasdaq()
print("Total symbols:", len(all_tickers))

# =============================
# TELEGRAM
# =============================

def send_message(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text}
        )
    except Exception as e:
        print("Telegram Error:", e)

send_message("🚀 STOCK + OPTION SCANNER STARTED")

# =============================
# OPTION CHECK
# =============================

def check_options(ticker, stock_price):

    if not market_is_open():
        return

    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options

        if not expirations:
            return

        exp = expirations[0]  # أقرب تاريخ فقط
        chain = stock.option_chain(exp)
        calls = chain.calls

        for _, row in calls.iterrows():

            option_price = row["lastPrice"]
            strike = row["strike"]
            volume = row["volume"]

            if strike > 100:
                continue

            if option_price is None or option_price == 0:
                continue

            if not (0.05 <= option_price <= 0.50):
                continue

            contract_id = f"{ticker}_{exp}_{strike}"

            if contract_id not in option_levels:
                option_levels[contract_id] = {
                    "entry": option_price,
                    "level": 0
                }

            entry = option_levels[contract_id]["entry"]
            change = ((option_price - entry) / entry) * 100
            last_level = option_levels[contract_id]["level"]

            if last_level == 0 and change >= 25:
                level = 25
            elif last_level >= 25 and change >= last_level + 10:
                level = last_level + 10
            else:
                continue

            if level > 400:
                continue

            option_levels[contract_id]["level"] = level

            now_ny = datetime.now(ny).strftime("%I:%M:%S %p")

            send_message(f"""
🔸 {ticker}
🟢 CALL OPTION LEVEL HIT

📅 Exp: {exp}
📌 Strike: {strike}
💲 Entry: {round(entry,2)}
💲 Current: {round(option_price,2)}
🚀 +{round(change,1)}%

🔥 Option Volume: {int(volume) if volume else 0}
🕒 {now_ny} NY
""")

    except:
        return

# =============================
# STOCK CHECK
# =============================

def check_stock(ticker):

    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d", interval="1m")

        if len(data) < 5:
            return

        price = data["Close"].iloc[-1]
        open_price = data["Open"].iloc[0]

        if open_price == 0:
            return

        if not (0.07 <= price <= 10):
            return

        change = ((price - open_price) / open_price) * 100
        accel = ((price - data["Close"].iloc[-4]) / data["Close"].iloc[-4]) * 100

        vol_1m = int(data["Volume"].iloc[-1])
        vol_2m = int(data["Volume"].iloc[-2:].sum())
        vol_5m = int(data["Volume"].iloc[-5:].sum())

        if ticker not in stock_levels:
            stock_levels[ticker] = 0

        last = stock_levels[ticker]
        abs_change = abs(change)

        if last == 0 and abs_change >= 3:
            level = 3
        elif last >= 3 and abs_change >= last + 3:
            level = last + 3
        else:
            check_options(ticker, price)
            return

        stock_levels[ticker] = level

        direction = "🟢" if change > 0 else "🔴"
        header = "BREAKOUT" if change > 0 else "BREAKDOWN"
        now_ny = datetime.now(ny).strftime("%I:%M:%S %p")

        send_message(f"""
🔸 {ticker}
{direction} STOCK {header}

💰 Price: {round(price,2)}$
📈 Daily Change: {round(change,2)}%
⚡ 3m Acceleration: {round(accel,2)}%

📊 1m Vol: {vol_1m:,}
📊 2m Vol: {vol_2m:,}
📊 5m Vol: {vol_5m:,}

🎯 Level {level}%
🕒 {now_ny} NY
""")

        check_options(ticker, price)

    except:
        return

# =============================
# MAIN LOOP
# =============================

index = 0
SCAN_DELAY = 1

while True:

    if index >= len(all_tickers):
        index = 0
        print("🔁 Restarting NASDAQ cycle")

    ticker = all_tickers[index]
    print("Scanning:", ticker)

    check_stock(ticker)

    index += 1
    time.sleep(SCAN_DELAY)
