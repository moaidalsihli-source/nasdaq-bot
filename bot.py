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

    # remove units / warrants / preferred
    df = df[~df["Symbol"].str.contains(r"\^|W$|R$|P$|U$")]

    # remove weird symbols
    df = df[~df["Symbol"].str.contains(r"\.|-")]

    # letters only
    df = df[df["Symbol"].str.match(r"^[A-Z]+$")]

    return df["Symbol"].tolist()

print("🚀 BOT STARTED")
all_tickers = get_nasdaq()
ticker_index = 0

# =============================
# MAIN LOOP
# =============================

while True:

    ticker = all_tickers[ticker_index]
    ticker_index = (ticker_index + 1) % len(all_tickers)

    if ticker in bad_tickers:
        continue

    try:
        data = yf.download(ticker, period="1d", interval="1m", progress=False)

        if data is None or data.empty or len(data) < 6:
            bad_tickers.add(ticker)
            continue

        close_series = data["Close"]
        open_series = data["Open"]

        if close_series.empty or open_series.empty:
            bad_tickers.add(ticker)
            continue

        price = float(close_series.iloc[-1].item())
        open_price = float(open_series.iloc[0].item())

        if open_price == 0:
            continue

        change = ((price - open_price) / open_price) * 100

        prev_price = float(close_series.iloc[-4].item())
        accel = ((price - prev_price) / prev_price) * 100

        vol_1m = int(data["Volume"].iloc[-1])
        vol_2m = int(data["Volume"].tail(2).sum())
        vol_5m = int(data["Volume"].tail(5).sum())

        # =============================
        # STOCK SIGNAL
        # =============================

        if 0.07 <= price <= 20 and abs(change) >= 3:

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

                        if pd.isna(last_price) or pd.isna(volume) or pd.isna(oi):
                            continue

                        if not (0.05 <= float(last_price) <= 0.50):
                            continue

                        if strike > 100:
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

🔥 Volume: {int(volume)}
🕒 {datetime.now(ny).strftime("%I:%M:%S %p")} NY
"""
                            send_message(message)
                            option_levels[key] = float(last_price)

    except:
        bad_tickers.add(ticker)

    time.sleep(1)
