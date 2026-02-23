import os
import time
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# =============================
# إعدادات تيليجرام
# =============================

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not TOKEN or not CHAT_ID:
    print("❌ ضع TOKEN و CHAT_ID في Railway")
    exit()

# =============================
# إعدادات البوت
# =============================

CHECK_INTERVAL = 120
PERCENT_TRIGGER = 2.8
MAX_PRICE = 10
MIN_TOTAL_VOLUME = 100000

alert_counter = 0
sent_today = {}

# =============================
# إيقاف السبت والأحد
# =============================

def weekend_stop():
    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)
    return now.weekday() >= 5

# =============================
# تحميل ناسدك
# =============================

def load_nasdaq():
    url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
    df = pd.read_csv(url, sep="|")
    df = df[df["Test Issue"] == "N"]
    return df["Symbol"].tolist()

print("تحميل قائمة ناسدك...")
NASDAQ = load_nasdaq()
print("تم تحميل", len(NASDAQ), "سهم")

# =============================
# إرسال رسالة
# =============================

def send_alert(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "disable_notification": False
    }
    requests.post(url, data=payload)

# =============================
# فحص سهم
# =============================

def check_symbol(symbol):
    global alert_counter

    stock = yf.Ticker(symbol)
    data = stock.history(period
