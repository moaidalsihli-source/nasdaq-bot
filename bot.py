import os
import requests
import yfinance as yf
import pandas as pd
import pytz
import time
import logging
from datetime import datetime

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

# ==============================
# ENV
# ==============================

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not TOKEN or not CHAT_ID:
    print("❌ TOKEN OR CHAT_ID NOT FOUND!")
    exit()

ny = pytz.timezone("America/New_York")

# ==============================
# SETTINGS
# ==============================

MIN_PRICE = 0.07
MAX_PRICE = 15
LEVEL_PERCENT = 3
DELAY = 1
OPTION_INTERVAL = 60

last_alert_time = 0
ALERT_COOLDOWN = 2
last_option_scan = 0

bad_tickers = set()
option_memory = {}

# ==============================
# TELEGRAM
# ==============================

def send_message(text):
    global last_alert_time
    now = time.time()

    if now - last_alert_time < ALERT_COOLDOWN:
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text}
        )
        last_alert_time = now
    except:
        pass

# ==============================
# MARKET TIME
# ==============================

def market_open():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 570 <= minutes <= 960  # 9:30 - 16:00

# ==============================
# NASDAQ 4 LETTER
# ==============================

def get_nasdaq_4():
    url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
    df = pd.read_csv(url, sep="|")

    df = df[df["Test Issue"] == "N"]
    df = df[df["ETF"] == "N"]
    df = df[df["Symbol"].str.match(r"^[A-Z]{4}$")]

    return df["Symbol"].tolist()

# ==============================
# STOCK SCAN
# ==============================

def scan_stock(ticker):

    if ticker in bad_tickers:
        return

    try:
        data = yf.download(
            ticker,
            period="1d",
            interval="1m",
            progress=False,
            threads=False
        )

        if data.empty or len(data) < 10:
            bad_tickers.add(ticker)
            return

        price = float(data["Close"].iloc[-1])
        open_price = float(data["Open"].iloc[0])

        if not (MIN_PRICE <= price <= MAX_PRICE):
            return

        change = ((price - open_price) / open_price) * 100
        accel_3m = ((data["Close"].iloc[-1] - data["Close"].iloc[-3]) /
                    data["Close"].iloc[-3]) * 100

        vol_1m = int(data["Volume"].iloc[-1])
        vol_2m = int(data["Volume"].iloc[-2:].sum())
        vol_5m = int(data["Volume"].iloc[-5:].sum())

        if abs(change) >= LEVEL_PERCENT:

            direction = "🟢 STOCK BREAKOUT" if change > 0 else "🔴 STOCK BREAKDOWN"

            message = f"""
🔸 {ticker}
{direction}

💰 Price: {round(price,2)}$
📈 Daily Change: {round(change,2)}%
⚡ 3m Acceleration: {round(accel_3m,2)}%

📊 1m Vol: {vol_1m:,}
📊 2m Vol: {vol_2m:,}
📊 5m Vol: {vol_5m:,}

🎯 Level {LEVEL_PERCENT}%
🕒 {datetime.now(ny).strftime("%I:%M:%S %p")} NY
"""
            send_message(message)

    except:
        bad_tickers.add(ticker)

# ==============================
# OPTION SCAN
# ==============================

def scan_options(ticker):

    if not market_open():
        return

    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options[:1]

        for exp in expirations:

            chain = stock.option_chain(exp)

            for opt_type, df_opt in [("CALL", chain.calls), ("PUT", chain.puts)]:

                for _, row in df_opt.iterrows():

                    last_price = row["lastPrice"]
                    volume = row["volume"]
                    strike = row["strike"]

                    if pd.isna(last_price) or pd.isna(volume):
                        continue

                    if not (0.05 <= float(last_price) <= 0.50):
                        continue

                    if strike > 100:
                        continue

                    key = f"{ticker}_{strike}_{opt_type}"

                    if key not in option_memory:
                        option_memory[key] = float(last_price)
                        continue

                    entry = option_memory[key]
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

🔥 Option Volume: {int(volume):,}
🕒 {datetime.now(ny).strftime("%I:%M %p")} NY
"""
                        send_message(message)
                        option_memory[key] = float(last_price)

    except:
        pass

# ==============================
# START
# ==============================

print("🚀 BOT STARTED")

send_message(f"""
🚀 NASDAQ SCANNER STARTED

📊 4 Letter Stocks Only
💰 Range: 0.07$ - 15$
🎯 Level: {LEVEL_PERCENT}%
⚙ Stock Scan: 1 per second
📈 Option Scan: 1 per minute (Market Hours)

🕒 {datetime.now(ny).strftime("%I:%M:%S %p")} NY
""")

tickers = get_nasdaq_4()
stock_index = 0
option_index = 0

while True:

    # ---- STOCK (1 كل 1 ثانية)
    ticker = tickers[stock_index]
    stock_index += 1
    if stock_index >= len(tickers):
        stock_index = 0

    scan_stock(ticker)

    # ---- OPTION (كل دقيقة)
    if market_open() and time.time() - last_option_scan >= OPTION_INTERVAL:

        opt_ticker = tickers[option_index]
        option_index += 1
        if option_index >= len(tickers):
            option_index = 0

        scan_options(opt_ticker)
        last_option_scan = time.time()

    time.sleep(DELAY)
