import json
import re
import sys
import time

import requests

BASE_URL = "https://app-lifgame-2026.azurewebsites.net"
DEBUG_ENDPOINT = f"{BASE_URL}/debug/execute"
WEBHOOK_ENDPOINT = f"{BASE_URL}/line/callback"


def get_real_user_id():
    print(">>> Fetching Real User ID from Cloud App...")
    payload = {"user_id": "debug_finder", "text": "/sys"}
    try:
        resp = requests.post(DEBUG_ENDPOINT, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        text = data.get("text", "")
        # Regex to find User ID
        match = re.search(r"Sample User: .+ \((U[0-9a-f]{32})\)", text)
        if match:
            return match.group(1)
        return None
    except Exception as e:
        print(f"FAILED TO FETCH ID: {e}")
        return None


def trigger_webhook_bypass(user_id, command_text):
    print(f">>> Triggering Logic for '{command_text}'...")

    webhook_body = {
        "destination": "Uexxxxx",
        "events": [
            {
                "type": "message",
                "message": {"type": "text", "id": "11111", "text": command_text},
                "timestamp": int(time.time() * 1000),
                "source": {"type": "user", "userId": user_id},
                "replyToken": "dummy_token_bypass",
                "mode": "active",
            }
        ],
    }

    headers = {"Content-Type": "application/json", "X-Debug-Bypass": "true", "X-Line-Signature": "dummy_sig"}

    try:
        resp = requests.post(WEBHOOK_ENDPOINT, json=webhook_body, headers=headers, timeout=20)
        print(f"Webhook Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        return resp.status_code == 200
    except Exception as e:
        print(f"REQUEST FAILED: {e}")
        return False


if __name__ == "__main__":
    uid = get_real_user_id()
    if not uid:
        print("No real user found, using dummy.")
        uid = "Udeadbeefdeadbeefdeadbeefdeadbeef"

    target_msg = "我想提升睪固酮到800~1200"
    trigger_webhook_bypass(uid, target_msg)
