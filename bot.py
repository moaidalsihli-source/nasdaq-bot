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
STEP = 3
BATCH_SIZE = 120
VOLUME_MULTIPLIER = 2
ny = pytz.timezone("America/New_York")
memory = {}

print("🚀 Mod F-15 ELITE LOADED")

# =========================
# وقت العمل
# =========================
def allowed_time():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    return 4 <= now.hour < 20

# =========================
# تحميل شركات ناسداك الحقيقية
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

        if data.empty or len(data) < 6:
            return

        open_price = data["Open"].iloc[0]
        current_price = data["Close"].iloc[-1]

        if not (MIN_PRICE <= current_price <= MAX_PRICE):
            return

        change = ((current_price - open_price) / open_price) * 100
        if abs(change) < STEP:
            return

        # ===== الفوليوم =====
        vol_1m = int(data["Volume"].iloc[-1])
        vol_2m = int(data["Volume"].iloc[-2:].sum())
        vol_5m_total = int(data["Volume"].iloc[-5:].sum())
        vol_5m_avg = vol_5m_total / 5

        # فلتر انفجار فوليوم
        if vol_1m < vol_5m_avg * VOLUME_MULTIPLIER:
            return

        level = int(abs(change) // STEP) * STEP
        direction = "🟢 صاعد" if change > 0 else "🔴 هابط"

        if symbol not in memory:
            memory[symbol] = []

        if level not in memory[symbol]:
            memory[symbol].append(level)

            print(f"""
🚀 Mod F-15 ELITE

🔸 الرمز -> {symbol}
🚨 تنبيه مستوى {level}%
⚡️ انفجار فوليوم
{direction}

💰 بدأ من -> {open_price:.4f}$
📍 الآن -> {current_price:.4f}$
📈 نسبة التغير -> {change:+.2f}%

📊 1m Vol -> {vol_1m:,}
📊 2m Vol -> {vol_2m:,}
📊 5m Avg -> {int(vol_5m_avg):,}

🕒 {datetime.now(ny).strftime('%I:%M:%S %p NY')}
""")

    except:
        pass

# =========================
# التشغيل الرئيسي
# =========================
def main():

    start_time = datetime.now(ny).strftime('%I:%M:%S %p NY')

    print(f"""
👑 Mod F-15 ELITE

📡 النظام بدأ الآن
🕒 {start_time}

📊 فلتر السعر: {MIN_PRICE}$ → {MAX_PRICE}$
📈 تنبيه كل {STEP}%
⚡ فلتر انفجار فوليوم مفعل
""")

    print("📊 تحميل شركات ناسداك...")
    symbols = get_nasdaq_symbols()
    print(f"✅ تم تحميل {len(symbols)} شركة (3 و 4 أحرف)")

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

        time.sleep(10)

if __name__ == "__main__":
    main()
