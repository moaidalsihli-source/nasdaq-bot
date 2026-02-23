import yfinance as yf
import time
import pytz
from datetime import datetime
import string

# =========================
# إعدادات
# =========================
MIN_PRICE = 0.06
MAX_PRICE = 10
STEP = 3
BATCH_SIZE = 100   # يفحص 100 كل 10 ثواني
TOTAL_SYMBOLS = 1000

ny = pytz.timezone("America/New_York")
memory = {}

print("🚀 Mod F-15 NASDAQ 1000 LOADED")

# =========================
def allowed_time():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    return 4 <= now.hour < 20

# =========================
# توليد 1000 رمز (1–4 حروف)
# =========================
def generate_symbols(limit=1000):
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

# =========================
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

            print(f"""
Mod F-15

🔸 الرمز -> {symbol}
🚨 تنبيه مستوى {level}%
⚪️ الإشارة -> زخم
{direction}

📍 الآن -> {current_price:.4f}$
📈 نسبة التغير -> {change:+.2f}%

🕒 {datetime.now(ny).strftime('%I:%M:%S %p NY')}
""")

    except:
        pass

# =========================
def main():

    print(f"""
🚀 Mod F-15

📡 بدأ الآن
📊 يفحص {TOTAL_SYMBOLS} سهم
🕒 {datetime.now(ny).strftime('%I:%M:%S %p NY')}
""")

    symbols = generate_symbols(TOTAL_SYMBOLS)
    index = 0

    while True:

        if not allowed_time():
            time.sleep(30)
            continue

        batch = symbols[index:index+BATCH_SIZE]

        for s in batch:
            scan(s)

        index += BATCH_SIZE
        if index >= len(symbols):
            index = 0

        time.sleep(10)  # كل 10 ثواني ينتقل لدفعة جديدة

if __name__ == "__main__":
    main()
