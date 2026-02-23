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
    print("TOKEN OR CHAT_ID NOT FOUND")
    exit()

ny = pytz.timezone("America/New_York")

# ==============================
# SETTINGS
# ==============================

MIN_PRICE = 0.20
MAX_PRICE = 10
DELAY = 1
OPTION_INTERVAL = 60

OPTION_LEVELS = [
    5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100,
    125, 150, 175, 200,
    250, 300, 350, 400, 450, 500, 550, 600,
    650, 700, 750, 800, 850, 900, 950, 1000
]

stock_levels = {}
option_memory = {}
last_option_scan = 0

# ==============================
# TELEGRAM
# ==============================

def send_message(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text}
        )
    except:
        pass

# ==============================
# TIME CONTROL
# ==============================

def stock_time_allowed():
    now = datetime.now(ny)

    if now.weekday() >= 5:
        return False

    minutes = now.hour * 60 + now.minute
    return 240 <= minutes <= 1200  # 4:00 AM → 8:00 PM


def option_market_open():
    now = datetime.now(ny)

    if now.weekday() >= 5:
        return False

    minutes = now.hour * 60 + now.minute
    return 570 <= minutes <= 960  # 9:30 AM → 4:00 PM


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
# STOCK SCAN (3% STEP)
# ==============================

def scan_stock(ticker):

    if not stock_time_allowed():
        return

    try:
        data = yf.download(
            ticker,
            period="1d",
            interval="1m",
            progress=False,
            threads=False
        )

        if data.empty:
            return

        price = float(data["Close"].iloc[-1])
        open_price = float(data["Open"].iloc[0])

        if not (MIN_PRICE <= price <= MAX_PRICE):
            return

        change = ((price - open_price) / open_price) * 100
        step = int(abs(change) // 3) * 3

        if step >= 3:

            direction = "UP" if change > 0 else "DOWN"
            key = f"{ticker}_{direction}"

            if key not in stock_levels:
                stock_levels[key] = 0

            if step > stock_levels[key]:

                stock_levels[key] = step
                direction_icon = "🟢 صاعد" if change > 0 else "🔴 هابط"

                message = f"""
Mod F-15

🔸 الرمز -> {ticker}
🚨 تنبيه مستوى {step}%
⚪️ الإشارة -> زخم
{direction_icon}

💰 بدأ من -> {round(open_price,2)}$
📍 الآن -> {round(price,2)}$
📈 نسبة التغير -> {round(change,2)}%

🕒 {datetime.now(ny).strftime("%I:%M:%S %p")} NY
"""
                send_message(message)

    except:
        pass


# ==============================
# OPTION SCAN
# ==============================

def scan_options(ticker):

    if not option_market_open():
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
                        option_memory[key] = {
                            "entry": float(last_price),
                            "last_level": 0
                        }
                        continue

                    entry = option_memory[key]["entry"]
                    gain = ((float(last_price) - entry) / entry) * 100

                    for level in OPTION_LEVELS:

                        if gain >= level and option_memory[key]["last_level"] < level:

                            option_memory[key]["last_level"] = level
                            direction = "🟢" if opt_type == "CALL" else "🔴"

                            message = f"""
Mod F-15 OPTIONS

🔸 الرمز -> {ticker}
{direction} {opt_type} OPTION LEVEL HIT

📅 تاريخ العقد -> {exp}
📌 Strike -> {strike}

💲 دخول -> {round(entry,2)}$
💲 الآن -> {round(float(last_price),2)}$
🚀 نسبة الربح -> +{round(gain,1)}%

🔥 حجم العقود -> {int(volume):,}
🕒 {datetime.now(ny).strftime("%I:%M %p")} NY
"""
                            send_message(message)

    except:
        pass


# ==============================
# START
# ==============================

print("🚀 Mod F-15 SCANNER STARTED")
send_message("🚀 Mod F-15 SCANNER STARTED")

tickers = get_nasdaq_4()
stock_index = 0
option_index = 0

while True:

    ticker = tickers[stock_index]
    stock_index += 1
    if stock_index >= len(tickers):
        stock_index = 0

    scan_stock(ticker)

    if time.time() - last_option_scan >= OPTION_INTERVAL:
        opt_ticker = tickers[option_index]
        option_index += 1
        if option_index >= len(tickers):
            option_index = 0

        scan_options(opt_ticker)
        last_option_scan = time.time()

    time.sleep(DELAY)
