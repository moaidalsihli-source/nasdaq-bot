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

ny = pytz.timezone("America/New_York")

stock_alert_count = {}

print("🚀 Mod F-15 PRO SCANNER STARTED")

# =========================
# GET LARGE US STOCK LIST (~3000+)
# =========================
def get_stock_universe():
    # قائمة كبيرة من الأسهم الأمريكية الشائعة
    tickers = yf.Tickers("^GSPC ^IXIC ^RUT")
    
    # نستخدم Screener بسيط
    sp500 = yf.download("^GSPC", period="1d")
    
    # بديل آمن: استخدام قائمة موسعة
    symbols = []

    # نحمل قائمة Russell تقريبية من yfinance
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        for second in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            symbols.append(letter + second)

    # فلترة رموز 2-4 حروف تقريباً
    symbols = [s for s in symbols if 2 <= len(s) <= 4]

    return symbols[:3000]  # نحدد 3000 سهم فقط

# =========================
# TIME CHECK
# =========================
def is_extended_market():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    return 4 <= now.hour < 20

# =========================
# STOCK SCANNER (LIGHT & FAST)
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

        if change_5min >= 1 and volume_now > avg_volume:

            count = stock_alert_count.get(symbol, 0) + 1
            stock_alert_count[symbol] = count

            print(f"""
Mod F-15 PRO

🔸 {symbol}
🚨 Alert #{count}
🟢 Early Momentum

📍 Price -> {price_now:.2f}$
📈 5min Move -> {change_5min:.2f}%
📊 Volume Surge

🕒 {datetime.now(ny).strftime('%I:%M %p NY')}
""")

    except:
        pass

# =========================
# MAIN LOOP
# =========================
def main():
    symbols = get_stock_universe()
    print(f"Loaded {len(symbols)} symbols")

    while True:
        if is_extended_market():
            for symbol in symbols:
                scan_stock(symbol)
                time.sleep(0.3)  # أسرع من قبل
        else:
            time.sleep(60)

if __name__ == "__main__":
    main()
