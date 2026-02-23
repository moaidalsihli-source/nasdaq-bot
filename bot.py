import yfinance as yf
import time
import pytz
from datetime import datetime
import pandas as pd

# =========================
# SETTINGS
# =========================
MIN_STOCK_PRICE = 0.20
MAX_STOCK_PRICE = 10

MIN_OPTION_PRICE = 0.15
MAX_OPTION_PRICE = 0.60

MIN_DELTA = 0.20
MAX_DELTA = 0.60

NASDAQ_SYMBOLS_URL = "https://old.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"

ny = pytz.timezone("America/New_York")

stock_alert_count = {}
option_entry_price = {}

print("🚀 Mod F-15 LIGHT SCANNER STARTED")

# =========================
# GET NASDAQ SYMBOLS (4 letters)
# =========================
def get_nasdaq_symbols():
    df = pd.read_csv(NASDAQ_SYMBOLS_URL, sep="|")
    symbols = df["Symbol"].tolist()
    symbols = [s for s in symbols if len(s) == 4 and s.isalpha()]
    return symbols

# =========================
# TIME CHECK
# =========================
def is_regular_market():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    return now.hour >= 9 and (now.hour < 16 or (now.hour == 9 and now.minute >= 30))

def is_extended_market():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    return 4 <= now.hour < 20

# =========================
# STOCK SCANNER (LIGHT MODE)
# =========================
def scan_stock(symbol):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d", interval="1m")

        if len(data) < 25:
            return

        price_now = data["Close"].iloc[-1]
        price_5min = data["Close"].iloc[-6]

        change_5min = ((price_now - price_5min) / price_5min) * 100

        volume_now = data["Volume"].iloc[-1]
        avg_volume = data["Volume"].rolling(20).mean().iloc[-1]

        if not (MIN_STOCK_PRICE <= price_now <= MAX_STOCK_PRICE):
            return

        # شرط خفيف
        if change_5min >= 1 and volume_now > avg_volume:

            count = stock_alert_count.get(symbol, 0) + 1
            stock_alert_count[symbol] = count

            print(f"""
Mod F-15 LIGHT MODE

🔸 الرمز -> {symbol}
🚨 تنبيه رقم {count}
🟢 زخم صاعد مبكر

📍 السعر الآن -> {price_now:.2f}$
📈 حركة 5 دقائق -> {change_5min:.2f}%
📊 فوليوم أعلى من المتوسط

🕒 {datetime.now(ny).strftime('%I:%M %p NY')}
""")

    except:
        pass

# =========================
# OPTION SCANNER
# =========================
def scan_options(symbol):
    if not is_regular_market():
        return

    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options

        for exp in expirations[:1]:
            chain = ticker.option_chain(exp)
            calls = chain.calls

            for _, row in calls.iterrows():
                price = row["lastPrice"]
                strike = row["strike"]
                delta = row.get("delta", None)
                volume = row["volume"]

                if price is None or delta is None:
                    continue

                if (
                    MIN_OPTION_PRICE <= price <= MAX_OPTION_PRICE and
                    MIN_DELTA <= delta <= MAX_DELTA and
                    volume >= 1000
                ):

                    key = f"{symbol}_{strike}_{exp}"

                    if key not in option_entry_price:
                        option_entry_price[key] = price

                    entry = option_entry_price[key]
                    gain = ((price - entry) / entry) * 100

                    levels = [5,10,20,30,40,50,75,100,150,200,300,400,500,750,1000]

                    for lvl in levels:
                        if gain >= lvl:
                            print(f"""
Mod F-15 OPTIONS

🔸 {symbol}
🟢 CALL OPTION

📅 Exp -> {exp}
📌 Strike -> {strike}
💲 Entry -> {entry:.2f}
💲 Current -> {price:.2f}
🚀 +{gain:.0f}%

🔥 Volume -> {int(volume)}
🕒 {datetime.now(ny).strftime('%I:%M %p NY')}
""")
                            break

    except:
        pass

# =========================
# MAIN LOOP
# =========================
def main():
    symbols = get_nasdaq_symbols()

    while True:
        for symbol in symbols:
            if is_extended_market():
                scan_stock(symbol)

            scan_options(symbol)

            time.sleep(1)  # سهم كل ثانية

if __name__ == "__main__":
    main()
