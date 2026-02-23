import yfinance as yf
import pandas as pd
import time
import pytz
from datetime import datetime

# =========================
# إعدادات
# =========================
MIN_PRICE = 0.06
MAX_PRICE = 10
STEP = 2
BATCH_SIZE = 120
ny = pytz.timezone("America/New_York")
memory = {}

# =========================
# تحميل شركات ناسداك
# =========================
def get_nasdaq_symbols():
    url = "https://ftp.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
    df = pd.read_csv(url, sep="|")
    symbols = df["Symbol"].tolist()
    symbols = [s for s in symbols if len(s) in [3,4]]
    return symbols

# =========================
# فحص السهم
# =========================
def scan(symbol):
    try:
        data = yf.Ticker(symbol).history(period="1d", interval="1m")

        if data.empty:
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

            # ===== Volume مع حماية =====
            try:
                vol_1m = int(data["Volume"].iloc[-1])
            except:
                vol_1m = 0

            try:
                vol_2m = int(data["Volume"].iloc[-2:].sum())
            except:
                vol_2m = 0

            try:
                vol_5m = int(data["Volume"].iloc[-5:].sum())
            except:
                vol_5m = 0

            print(f"""
Mod F-15

🔸 الرمز -> {symbol}
🚨 تنبيه مستوى {level}%
{direction}

📍 الآن -> {current_price:.4f}$
📈 نسبة التغير -> {change:+.2f}%

📊 1m Vol -> {vol_1m:,}
📊 2m Vol -> {vol_2m:,}
📊 5m Vol -> {vol_5m:,}

🕒 {datetime.now(ny).strftime('%I:%M:%S %p NY')}
""")

    except:
        pass

# =========================
# التشغيل الرئيسي
# =========================
def main():

    print("🚀 BOT STARTED NOW")
    print(f"🕒 {datetime.now(ny).strftime('%I:%M:%S %p NY')}")
    print("📊 تحميل شركات ناسداك...")

    symbols = get_nasdaq_symbols()
    print(f"✅ تم تحميل {len(symbols)} شركة")

    index = 0

    while True:

        batch = symbols[index:index+BATCH_SIZE]

        for s in batch:
            scan(s)

        index += BATCH_SIZE
        if index >= len(symbols):
            index = 0

        time.sleep(10)

if __name__ == "__main__":
    main()
