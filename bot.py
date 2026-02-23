import yfinance as yf
import time
import pytz
from datetime import datetime
import string

MIN_STOCK_PRICE = 0.20
MAX_STOCK_PRICE = 10

ny = pytz.timezone("America/New_York")
stock_alert_count = {}

print("🚀 Mod F-15 SMART SCANNER STARTED")

# =========================
# توليد رموز 1-4 أحرف
# =========================
def generate_symbols():
    letters = string.ascii_uppercase
    symbols = []

    # 1 حرف
    for a in letters:
        symbols.append(a)

    # 2 حروف
    for a in letters:
        for b in letters:
            symbols.append(a+b)

    # 3 حروف
    for a in letters:
        for b in letters:
            for c in letters:
                symbols.append(a+b+c)

    # 4 حروف
    for a in letters:
        for b in letters:
            for c in letters:
                for d in letters:
                    symbols.append(a+b+c+d)

    return symbols


# =========================
def is_extended_market():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    return 4 <= now.hour < 20


# =========================
def scan_stock(symbol):
    try:
        data = yf.Ticker(symbol).history(period="1d", interval="1m")

        if data.empty or len(data) < 25:
            return

        price_now = data["Close"].iloc[-1]
        price_5min = data["Close"].iloc[-6]

        change_5min = ((price_now - price_5min) / price_5min) * 100

        volume_now = data["Volume"].iloc[-1]
        avg_volume = data["Volume"].rolling(20).mean().iloc[-1]

        if not (MIN_STOCK_PRICE <= price_now <= MAX_STOCK_PRICE):
            return

        if change_5min >= 1 and volume_now > avg_volume:

            count = stock_alert_count.get(symbol, 0) + 1
            stock_alert_count[symbol] = count

            print(f"""
Mod F-15

🔸 {symbol}
🚨 Alert #{count}
🟢 Early Momentum

📍 Price -> {price_now:.2f}$
📈 5min Move -> {change_5min:.2f}%
📊 Volume Surge

🕒 {datetime.now(ny).strftime('%I:%M %p NY')}
""")

    except:
        return


# =========================
def main():
    symbols = generate_symbols()
    total = len(symbols)
    print(f"Generated {total} symbols")

    index = 0

    while True:

        if not is_extended_market():
            time.sleep(60)
            continue

        print("⏱ New 60-stock batch")

        batch = symbols[index:index+60]

        for symbol in batch:
            scan_stock(symbol)
            time.sleep(0.3)

        index += 60

        if index >= total:
            index = 0  # يرجع من البداية

        time.sleep(60)


if __name__ == "__main__":
    main()
