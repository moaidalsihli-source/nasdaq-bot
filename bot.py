import os
import requests
import time

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

names = ["عواطف", "ريمان", "ريماس"]

for name in names:
    data = {
        "chat_id": CHAT_ID,
        "text": name
    }

    r = requests.post(url, data=data)
    print(f"Sent {name}:", r.text)

    time.sleep(1)
