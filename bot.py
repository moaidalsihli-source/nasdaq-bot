import yfinance as yf
import time
import pytz
from datetime import datetime
import string

# =========================
# SETTINGS
# =========================
MIN_OPTION_PRICE = 0.15
MAX_OPTION_PRICE = 0.60

OPTION_LEVELS = [5,10,20,30,40,50,75,100,150,200,300,400,500,750,1000]

ny = pytz.timezone("America/New_York")

option_memory = {}

print("🚀 Mod F-15 GLOBAL OPTIONS STARTED")

# =========================
# وقت السوق الرسمي فقط
# =========================
def is_regular_market():
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    return (now.hour > 9 or (now.hour == 9 and now.minute >= 30)) and now.hour < 16


# =========================
# توليد رموز 1–4 أحرف
# =========================
def generate_symbols(limit=5000):
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

                    if len(symbols) >= limit:
                        return symbols

    return symbols


# =========================
# فحص العقود
# =========================
def scan_options(symbol):

    if not is_regular_market():
        return

    try:
        ticker = yf.Ticker(symbol)

        expirations = ticker.options
        if not expirations:
            return

        exp = expirations[0]  # أول تاريخ فقط لتخفيف الضغط
        chain = ticker.option_chain(exp)

        calls = chain.calls

        for _, row in calls.iterrows():

            price = row["lastPrice"]
            strike = row["strike"]
            volume = row["volume"]

            if price is None:
                continue

            if not (MIN_OPTION_PRICE <= price <= MAX_OPTION_PRICE):
                continue

            key = f"{symbol}_{strike}_{exp}"

            if key not in option_memory:
                option_memory[key] = {
                    "entry": price,
                    "levels_hit": []
                }

            entry = option_memory[key]["entry"]
            gain = ((price - entry) / entry) * 100

            for lvl in OPTION_LEVELS:
                if gain >= lvl and lvl not in option_memory[key]["levels_hit"]:

                    option_memory[key]["levels_hit"].append(lvl)

                    print(f"""
Mod F-15 OPTIONS

🔸 الرمز -> {symbol}
🟢 CALL OPTION LEVEL HIT

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
# MAIN LOOP (60 شركة كل دقيقة)
# =========================
def main():

    symbols = generate_symbols(5000)
    print(f"Generated {len(symbols)} symbols")

    index = 0
    total = len(symbols)

    while True:

        if not is_regular_market():
            time.sleep(60)
            continue

        print("⏱ New 60-stock batch")

        batch = symbols[index:index+60]

        for symbol in batch:
            scan_options(symbol)
            time.sleep(0.5)

        index += 60
        if index >= total:
            index = 0

        time.sleep(60)


if __name__ == "__main__":
    main()
