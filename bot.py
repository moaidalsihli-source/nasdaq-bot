import os
import requests
import yfinance as yf
import pandas as pd
import pytz
import time
import logging
from datetime import datetime, timedelta

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
OPTION_LEVELS = [25, 50, 100, 200, 400]

bad_tickers = set()
option_memory = {}
last_alert_time_stock = {}
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
# MARKET TIME
# ==============================

def market_open():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 570 <= minutes <= 960

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

    if ticker in last_alert_time_stock:
        if datetime.now() - last_alert_time_stock[ticker] < timedelta(minutes=10):
            return

    try:
        data = yf.download(
            ticker,
            period="1d",
            interval="1m",
            progress=False,
            threads=False
        )

        if data.empty or len(data) < 20:
            bad_tickers.add(ticker)
            return

        price = float(data["Close"].iloc[-1])
        open_price = float(data["Open"].iloc[0])

        if not (MIN_PRICE <= price <= MAX_PRICE):
            return

        daily_change = ((price - open_price) / open_price) * 100

        data["EMA9"] = data["Close"].ewm(span=9).mean()
        data["EMA20"] = data["Close"].ewm(span=20).mean()

        ema9 = float(data["EMA9"].iloc[-1])
        ema20 = float(data["EMA20"].iloc[-1])

        data["VWAP"] = (data["Close"] * data["Volume"]).cumsum() / data["Volume"].cumsum()
        vwap = float(data["VWAP"].iloc[-1])

        vol_now = int(data["Volume"].iloc[-1])
        avg_vol = int(data["Volume"].iloc[-20:].mean())

        if avg_vol == 0:
            return

        volume_spike = vol_now > avg_vol * 2

        trend_up = ema9 > ema20 and price > vwap
        trend_down = ema9 < ema20 and price < vwap

        if abs(daily_change) >= LEVEL_PERCENT and volume_spike:

            if daily_change > 0 and trend_up:
                direction = "🟢 صاعد قوي"
            elif daily_change < 0 and trend_down:
                direction = "🔴 هابط قوي"
            else:
                return

            message = f"""
🔸 {ticker}
🚨 Institutional Momentum

📈 الاتجاه -> {direction}
💰 السعر -> {round(price,2)}$ ({round(daily_change,2)}%)

🔥 Volume Spike x{round(vol_now/avg_vol,1)}
📊 EMA9 > EMA20: {ema9 > ema20}
📊 Above VWAP: {price > vwap}

🕒 {datetime.now(ny).strftime("%I:%M:%S %p")} NY
"""
            send_message(message)
            last_alert_time_stock[ticker] = datetime.now()

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
                        option_memory[key] = {
                            "entry": float(last_price),
                            "last_level": 0
                        }
                        continue

                    entry = option_memory[key]["entry"]
                    gain = ((float(last_price) - entry) / entry) * 100

                    for level in OPTION_LEVELS:

                        if gain >= level and option_memory[key]["last_level"] < level:

                            direction = "🟢" if opt_type == "CALL" else "🔴"

                            message = f"""
🔸 {ticker}
{direction} {opt_type} OPTION

📌 Strike: {strike}
💲 Entry: {round(entry,2)}
💲 Current: {round(float(last_price),2)}

🚀 +{level}% HIT
📈 Gain: +{round(gain,1)}%
🔥 Volume: {int(volume):,}

🕒 {datetime.now(ny).strftime("%I:%M %p")} NY
"""
                            send_message(message)
                            option_memory[key]["last_level"] = level

    except:
        pass

# ==============================
# START
# ==============================

print("🚀 ELITE NASDAQ SCANNER STARTED")
send_message("🚀 ELITE NASDAQ SCANNER STARTED")

tickers = get_nasdaq_4()
stock_index = 0
option_index = 0

while True:

    ticker = tickers[stock_index]
    stock_index += 1
    if stock_index >= len(tickers):
        stock_index = 0

    scan_stock(ticker)

    if market_open() and time.time() - last_option_scan >= OPTION_INTERVAL:

        opt_ticker = tickers[option_index]
        option_index += 1
        if option_index >= len(tickers):
            option_index = 0

        scan_options(opt_ticker)
        last_option_scan = time.time()

    time.sleep(DELAY)
