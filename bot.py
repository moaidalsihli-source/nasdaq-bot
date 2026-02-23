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

# =============================
# SETTINGS
# =============================

BATCH_SIZE = 5
DELAY = 10
ALERT_INTERVAL = 5  # منع سبام تلغرام

last_alert_time = 0
option_levels = {}
bad_tickers = set()

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
    except:
        pass

# =============================
# MARKET TIME
# =============================

def market_is_open():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 570 <= minutes <= 960

# =============================
# NASDAQ CLEAN LIST
# =============================

def get_nasdaq():
    url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
    df = pd.read_csv(url, sep="|")

    df = df[df["Test Issue"] == "N"]
    df = df[df["ETF"] == "N"]

    df = df[~df["Symbol"].str.contains(r"\^|W$|R$|P$|U$")]
    df = df[~df["Symbol"].str.contains(r"\.|-")]
    df = df[df["Symbol"].str.match(r"^[A-Z]+$")]

    return df["Symbol"].tolist()

# =============================
# OPTION CHECK (فقط عند الإشارة)
# =============================

def check_options(ticker):
    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options[:2]  # فقط أول تاريخين

        for exp in expirations:

            chain = stock.option_chain(exp)

            for opt_type, df_opt in [("CALL", chain.calls), ("PUT", chain.puts)]:

                for _, row in df_opt.iterrows():

                    last_price = row["lastPrice"]
                    volume = row["volume"]
                    oi = row["openInterest"]
                    strike = row["strike"]

                    if pd.isna(last_price) or pd.isna(volume) or pd.isna(oi):
                        continue

                    if not (0.05 <= float(last_price) <= 0.50):
                        continue

                    if volume < 5000 or oi < 3000:
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
{direction} {opt_type} OPTION

📅 Exp: {exp}
📌 Strike: {strike}
💲 Entry: {round(entry,2)}
💲 Now: {round(float(last_price),2)}
🚀 +{round(gain,1)}%
"""
                        send_message(message)
                        option_levels[key] = float(last_price)

    except:
        pass

# =============================
# START
# =============================

print("🚀 BOT STARTED")
all_tickers = get_nasdaq()
ticker_index = 0

# =============================
# MAIN LOOP
# =============================

while True:

    batch = all_tickers[ticker_index:ticker_index+BATCH_SIZE]
    ticker_index += BATCH_SIZE

    if ticker_index >= len(all_tickers):
        ticker_index = 0

    for ticker in batch:

        if ticker in bad_tickers:
            continue

        try:
            data = yf.download(
                ticker,
                period="1d",
                interval="1m",
                progress=False
            )

            if data is None or data.empty or len(data) < 5:
                bad_tickers.add(ticker)
                continue

            price = float(data["Close"].iloc[-1])
            open_price = float(data["Open"].iloc[0])

            if open_price == 0:
                continue

            change = ((price - open_price) / open_price) * 100

            if 0.07 <= price <= 20 and abs(change) >= 3:

                direction = "🟢" if change > 0 else "🔴"
                header = "BREAKOUT" if change > 0 else "BREAKDOWN"

                message = f"""
🔸 {ticker}
{direction} STOCK {header}

💰 Price: {round(price,2)}$
📈 Move: {round(change,2)}%
🕒 {datetime.now(ny).strftime("%I:%M:%S %p")} NY
"""
                send_message(message)

                # فحص الأوبشن فقط عند الإشارة
                if market_is_open():
                    check_options(ticker)

        except:
            bad_tickers.add(ticker)

    time.sleep(DELAY)
