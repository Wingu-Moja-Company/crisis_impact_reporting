"""
One-shot script: (re-)registers the Telegram webhook with a secret_token so
that every incoming update carries X-Telegram-Bot-Api-Secret-Token for
server-side signature verification.

Run this once after setting TELEGRAM_WEBHOOK_SECRET in Azure App Settings:

    cd bot
    TELEGRAM_BOT_TOKEN=<token> \
    TELEGRAM_WEBHOOK_SECRET=<secret> \
    WEBHOOK_URL=https://func-crisis-bot-ob7ravt3zfbzi.azurewebsites.net/api/webhook \
    python register_webhook.py

The script prints the Telegram API response.  Expected: {"ok":true,...}
"""

import os
import urllib.request
import json

TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
SECRET  = os.environ["TELEGRAM_WEBHOOK_SECRET"]
URL     = os.environ["WEBHOOK_URL"]

payload = json.dumps({
    "url": URL,
    "secret_token": SECRET,
    "allowed_updates": ["message", "callback_query"],
    "drop_pending_updates": True,
}).encode()

req = urllib.request.Request(
    f"https://api.telegram.org/bot{TOKEN}/setWebhook",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read())

print(json.dumps(result, indent=2))
if result.get("ok"):
    print("\n✓ Webhook registered successfully with secret_token.")
else:
    print("\n✗ Registration failed — check the output above.")
