import yfinance as yf
import time
import pytz
from datetime import datetime
import string

MIN_PRICE = 0.20
MAX_PRICE = 10
STEP = 3
BATCH_SIZE = 60

ny = pytz.timezone("America/New_York")
memory = {}

print("🚀 Mod F-15 FULL MOMENTUM STARTED")

def allowed_time():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    return 4 <= now.hour < 20  # 4AM → 8PM

def generate_symbols(limit=3000):
    letters = string.ascii_uppercase
    symbols = []

    for a in letters:
        symbols.append(a)

    for a in letters:
        for b in letters:
            symbols.append(a+b)

    for a in letters:
        for b in letters:
            for c in letters:
                symbols.append(a+b+c)

    for a in letters:
        for b in letters:
            for c in letters:
                for d in letters:
                    symbols.append(a+b+c+d)
                    if len(symbols) >= limit:
                        return symbols

    return symbols

def scan(symbol):
    try:
        data = yf.Ticker(symbol).history(period="1d", interval="1m")

        if data.empty or len(data) < 6:
            return

        open_price = data["Open"].iloc[0]
        current_price = data["Close"].iloc[-1]

        if not (MIN_PRICE <= current_price <= MAX_PRICE):
            return

        change = ((current_price - open_price) / open_price) * 100

        if abs(change) < STEP:
            return

        level = int(abs(change) // STEP) * STEP
        direction = "🟢 صاعد" if change > 0 else "🔴 هابط"

        if symbol not in memory:
            memory[symbol] = []

        if level not in memory[symbol]:
            memory[symbol].append(level)

            # Volume calculations
            vol_1m = int(data["Volume"].iloc[-1])
            vol_2m = int(data["Volume"].iloc[-2:].sum())
            vol_5m = int(data["Volume"].iloc[-5:].sum())

            print(f"""
Mod F-15

🔸 الرمز -> {symbol}
🚨 تنبيه مستوى {level}%
⚪️ الإشارة -> زخم
{direction}

💰 بدأ من -> {open_price:.2f}$
📍 الآن -> {current_price:.2f}$
📈 نسبة التغير -> {change:+.2f}%

📊 1m Vol -> {vol_1m:,}
📊 2m Vol -> {vol_2m:,}
📊 5m Vol -> {vol_5m:,}

🕒 {datetime.now(ny).strftime('%I:%M:%S %p NY')}
""")

    except:
        pass

def main():
    symbols = generate_symbols(3000)
    index = 0

    while True:

        if not allowed_time():
            time.sleep(60)
            continue

        batch = symbols[index:index+BATCH_SIZE]

        for s in batch:
            scan(s)
            time.sleep(0.3)

        index += BATCH_SIZE
        if index >= len(symbols):
            index = 0

        time.sleep(60)

if __name__ == "__main__":
    main()
