import yfinance as yf
import time
import pytz
from datetime import datetime

# =========================
# SETTINGS
# =========================
MIN_STOCK_PRICE = 0.20
MAX_STOCK_PRICE = 10

MIN_OPTION_PRICE = 0.15
MAX_OPTION_PRICE = 0.60

OPTION_LEVELS = [5,10,20,30,40,50,75,100,150,200,300,400,500,750,1000]

ny = pytz.timezone("America/New_York")

stock_memory = {}
option_memory = {}

WATCHLIST = ["NIVF","SOFI","NVDA","TSLA","LCID","RIVN","MARA","RIOT"]

print("🚀 Mod F-15 MOMENTUM PRO STARTED")

# =========================
# TIME FILTERS
# =========================

def stock_time_allowed():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    # Pre 4am → After 8pm
    return 4 <= now.hour < 20

def option_time_allowed():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    return (now.hour > 9 or (now.hour == 9 and now.minute >= 30)) and now.hour < 16

# =========================
# STOCK MOMENTUM
# =========================

def scan_stock(symbol):
    if not stock_time_allowed():
        return

    try:
        data = yf.Ticker(symbol).history(period="1d", interval="1m")

        if data.empty or len(data) < 30:
            return

        session_open = data["Open"].iloc[0]
        price_now = data["Close"].iloc[-1]

        if not (MIN_STOCK_PRICE <= price_now <= MAX_STOCK_PRICE):
            return

        change = ((price_now - session_open) / session_open) * 100
        level = int(abs(change) // 3) * 3

        if level < 3:
            return

        direction = "🟢 صاعد" if change > 0 else "🔴 هابط"

        if symbol not in stock_memory:
            stock_memory[symbol] = []

        if level not in stock_memory[symbol]:
            stock_memory[symbol].append(level)

            print(f"""
Mod F-15

🔸 الرمز -> {symbol}
🚨 تنبيه مستوى {level}%
⚪️ الإشارة -> زخم
{direction}

💰 بدأ من -> {session_open:.2f}$
📍 الآن -> {price_now:.2f}$
📈 نسبة التغير -> {change:+.2f}%

🕒 {datetime.now(ny).strftime('%I:%M:%S %p NY')}
""")

    except:
        pass

# =========================
# OPTION MOMENTUM
# =========================

def scan_options(symbol):
    if not option_time_allowed():
        return

    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options

        if not expirations:
            return

        exp = expirations[0]
        chain = ticker.option_chain(exp)

        for option_type, df in [("CALL", chain.calls), ("PUT", chain.puts)]:

            for _, row in df.iterrows():

                price = row["lastPrice"]
                strike = row["strike"]
                volume = row["volume"]

                if price is None:
                    continue

                if not (MIN_OPTION_PRICE <= price <= MAX_OPTION_PRICE):
                    continue

                key = f"{symbol}_{strike}_{exp}_{option_type}"

                if key not in option_memory:
                    option_memory[key] = {
                        "entry": price,
                        "levels": []
                    }

                entry = option_memory[key]["entry"]
                gain = ((price - entry) / entry) * 100

                for lvl in OPTION_LEVELS:
                    if gain >= lvl and lvl not in option_memory[key]["levels"]:

                        option_memory[key]["levels"].append(lvl)

                        print(f"""
Mod F-15 OPTIONS

🔸 الرمز -> {symbol}
🟢 {option_type} OPTION LEVEL HIT

📅 تاريخ العقد -> {exp}
📌 Strike -> {strike}

💲 دخول -> {entry:.2f}$
💲 الآن -> {price:.2f}$
🚀 نسبة الربح -> +{gain:.0f}%

🔥 حجم العقود -> {int(volume) if volume else 0:,}
🕒 {datetime.now(ny).strftime('%I:%M %p NY')}
""")

    except:
        pass

# =========================
# MAIN LOOP
# =========================

def main():
    while True:

        for symbol in WATCHLIST:
            scan_stock(symbol)
            scan_options(symbol)
            time.sleep(2)

        time.sleep(30)

if __name__ == "__main__":
    main()
