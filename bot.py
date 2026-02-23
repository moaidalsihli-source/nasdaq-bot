import os
import requests

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

print("TOKEN:", TOKEN)
print("CHAT_ID:", CHAT_ID)

url = f"https://api.telegram.org/bot{TOKEN}/getMe"
r = requests.get(url)

print("Telegram Response:", r.text)
