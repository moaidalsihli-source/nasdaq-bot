import os
import requests
import time

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=data)

# تجربة إرسال من 1 إلى 100
for i in range(1, 101):
    send_message(str(i))
    time.sleep(2)  # يرسل كل رقم كل ثانيتين
