"""
Broadcast an SMS activation message via Africa's Talking.

Usage:
    python scripts/sms_broadcast.py \
        --region nairobi \
        --message "Crisis reporting is now active. Submit reports at https://report.crisisplatform.io"
"""

import argparse
import os
import urllib.parse
import urllib.request


def broadcast(region: str, message: str) -> None:
    api_key  = os.environ["AT_API_KEY"]
    username = os.environ["AT_USERNAME"]

    # Africa's Talking bulk SMS endpoint
    url = "https://api.africastalking.com/version1/messaging"
    payload = urllib.parse.urlencode({
        "username": username,
        "to":       f"+{region}",  # In production, replace with a recipient list or shortcode
        "message":  message,
    }).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "apiKey": api_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = resp.read().decode()
    print(f"SMS broadcast sent to region '{region}'.")
    print(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Broadcast SMS via Africa's Talking")
    parser.add_argument("--region",  required=True, help="Region name or dial prefix")
    parser.add_argument("--message", required=True, help="SMS message text")
    args = parser.parse_args()
    broadcast(args.region, args.message)


if __name__ == "__main__":
    main()
