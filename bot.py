import os
import requests
import yfinance as yf
import pandas as pd
import pytz
import time
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

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
# CLEAN NASDAQ LIST
# =============================

def get_nasdaq():
    url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
    df = pd.read_csv(url, sep="|")

    df = df[df["Test Issue"] == "N"]
    df = df[df["ETF"] == "N"]
    df = df[df["NextShares"] == "N"]

    tickers = df["Symbol"].tolist()

    clean = []
    for t in tickers:
        if (
            isinstance(t, str)
            and "-" not in t
            and "." not in t
            and "^" not in t
            and "/" not in t
            and len(t) <= 5
        ):
            clean.append(t)

    return clean

print("Loading NASDAQ...")
all_tickers = get_nasdaq()
print("Clean symbols:", len(all_tickers))

# =============================
# TELEGRAM
# =============================

def send_message(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text}
        )
    except:
        pass

def send_startup():
    now_ny = datetime.now(ny).strftime("%I:%M:%S %p")
    send_message(f"""
🚀 NASDAQ SCANNER STARTED

📊 Stocks: 3% then +3%
📑 Options: 25% then +10%
🕒 {now_ny} NY
""")

send_startup()

# =============================
# STOCK ALERT
# =============================

def check_stock(ticker, price, change, accel):

    if ticker not in stock_levels:
        stock_levels[ticker] = 0

    last = stock_levels[ticker]
    abs_change = abs(change)

    if last == 0 and abs_change >= 3:
        level = 3
    elif last >= 3 and abs_change >= last + 3:
        level = last + 3
    else:
        return

    stock_levels[ticker] = level

    direction = "🟢" if change > 0 else "🔴"
    header = "BREAKOUT" if change > 0 else "BREAKDOWN"
    now_ny = datetime.now(ny).strftime("%I:%M:%S %p")

    send_message(f"""
🔸 {ticker}
{direction} STOCK {header}

💰 {round(price,2)}$
📊 {round(change,2)}%
🎯 Level {level}%
⚡ Accel {round(accel,2)}

🕒 {now_ny}
""")

# =============================
# OPTION ALERT
# =============================

def check_option(ticker, exp, strike, current_price, volume, direction):

    key = f"{ticker}_{strike}_{exp}"

    if key not in option_levels:
        option_levels[key] = {
            "entry": current_price,
            "last": 0
        }
        return

    entry = option_levels[key]["entry"]
    last = option_levels[key]["last"]

    change = ((current_price - entry) / entry) * 100

    if last == 0 and change >= 25:
        level = 25
    elif last >= 25 and change >= last + 10:
        level = last + 10
    else:
        return

    option_levels[key]["last"] = level

    color = "🟢 CALL" if direction == "CALL" else "🔴 PUT"
    now_ny = datetime.now(ny).strftime("%I:%M:%S %p")

    send_message(f"""
🔸 {ticker}
{color} OPTION

📅 {exp}
📌 Strike {strike}
💲 Entry {round(entry,2)}
💲 Now {round(current_price,2)}
🚀 +{level}%
🔥 Vol {int(volume)}

🕒 {now_ny}
""")

# =============================
# SCAN ONE STOCK
# =============================

def scan_stock(ticker):

    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d", interval="1m", prepost=False)

        if len(data) < 5:
            return

        price = data["Close"].iloc[-1]
        open_price = data["Open"].iloc[0]
        change = ((price - open_price) / open_price) * 100
        accel = ((price - data["Close"].iloc[-4]) / data["Close"].iloc[-4]) * 100

        if not (0.07 <= price <= 10):
            return

        check_stock(ticker, price, change, accel)

        if not market_is_open():
            return

        direction = "CALL" if change > 0 else "PUT"

        for exp in stock.options[:2]:  # فقط أقرب تاريخين
            chain = stock.option_chain(exp)
            options = chain.calls if direction == "CALL" else chain.puts

            for _, row in options.iterrows():

                opt_price = row["lastPrice"]
                strike = row["strike"]
                vol = row["volume"]

                if pd.isna(opt_price) or pd.isna(vol):
                    continue

                if 0.05 <= opt_price <= 0.50 and vol > 50:
                    check_option(
                        ticker, exp, strike,
                        opt_price, vol, direction
                    )

    except Exception as e:
        print(f"Error {ticker}: {e}")

# =============================
# MAIN LOOP
# =============================

while True:

    sample = random.sample(all_tickers, 250)

    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(scan_stock, sample)

    time.sleep(15)
