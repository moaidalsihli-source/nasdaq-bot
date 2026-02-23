import os
import requests
import time

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

for i in range(1, 51):
    data = {
        "chat_id": CHAT_ID,
        "text": str(i)
    }

    r = requests.post(url, data=data)
    print(f"Sent {i}:", r.text)

    time.sleep(1)  # انتظار ثانية بين كل رسالة
