"""
Register the Telegram bot webhook with the live Azure Functions URL.

Usage:
    python scripts/register_telegram_webhook.py --env prod
    python scripts/register_telegram_webhook.py --env dev --url https://ngrok.io/api/telegram
"""

import argparse
import json
import os
import urllib.request


def register(token: str, webhook_url: str, secret: str | None) -> None:
    params = {"url": webhook_url}
    if secret:
        params["secret_token"] = secret

    payload = json.dumps(params).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/setWebhook",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())

    if result.get("ok"):
        print(f"Webhook registered: {webhook_url}")
    else:
        print(f"ERROR: {result}")
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Register Telegram bot webhook")
    parser.add_argument("--env", choices=["dev", "prod"], default="prod")
    parser.add_argument("--url", default=None, help="Override webhook URL (optional)")
    args = parser.parse_args()

    token  = os.environ["TELEGRAM_BOT_TOKEN"]
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET")

    if args.url:
        webhook_url = args.url
    elif args.env == "prod":
        func_app = os.environ["AZURE_FUNCTIONS_APP_NAME"]
        webhook_url = f"https://{func_app}.azurewebsites.net/api/telegram"
    else:
        webhook_url = os.environ["DEV_WEBHOOK_URL"]

    register(token, webhook_url, secret)


if __name__ == "__main__":
    main()
