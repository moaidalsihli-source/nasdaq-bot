import yfinance as yf
import time
import pytz
from datetime import datetime

# =========================
# إعدادات
# =========================
MIN_PRICE = 0.06
MAX_PRICE = 10
STEP = 3  # كل 3%
ny = pytz.timezone("America/New_York")
memory = {}

print("🚀 Mod F-15 NASDAQ PENNY MOMENTUM LOADED")

# =========================
# وقت العمل (4AM → 8PM NY)
# =========================
def allowed_time():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    return 4 <= now.hour < 20

# =========================
# قائمة ناسداك (يمكنك تكبيرها)
# =========================
def get_nasdaq_symbols():
    return [
        "SIRI","LCID","RIVN","NKLA","HOOD","PLTR","SOFI","NIO","XPEV","BB",
        "CENN","FFIE","MULN","GME","AMC","RIOT","MARA","TTOO","IDEX","SNDL",
        "AAPL","MSFT","NVDA","AMD","TSLA"
    ]

# =========================
# فحص الزخم
# =========================
def scan(symbol):
    try:
        data = yf.Ticker(symbol).history(period="1d", interval="1m")

        if data.empty or len(data) < 6:
            return

        open_price = data["Open"].iloc[0]
        current_price = data["Close"].iloc[-1]

        # فلتر السعر
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

            vol_1m = int(data["Volume"].iloc[-1])
            vol_2m = int(data["Volume"].iloc[-2:].sum())
            vol_5m = int(data["Volume"].iloc[-5:].sum())

            print(f"""
Mod F-15

🔸 الرمز -> {symbol}
🚨 تنبيه مستوى {level}%
⚪️ الإشارة -> زخم
{direction}

💰 بدأ من -> {open_price:.4f}$
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

    print(f"""
🚀 Mod F-15

📡 بدأ الآن
📊 فلتر السعر: {MIN_PRICE}$ → {MAX_PRICE}$
🕒 {datetime.now(ny).strftime('%I:%M:%S %p NY')}
""")

    symbols = get_nasdaq_symbols()

    while True:

        if not allowed_time():
            time.sleep(60)
            continue

        for s in symbols:
            scan(s)
            time.sleep(1)

        time.sleep(30)

if __name__ == "__main__":
    main()
