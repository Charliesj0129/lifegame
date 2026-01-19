import requests
import json
import re
import sys
import time

BASE_URL = "https://app-lifgame-2026.azurewebsites.net"
DEBUG_ENDPOINT = f"{BASE_URL}/debug/execute"
WEBHOOK_ENDPOINT = f"{BASE_URL}/line/callback"


def initialize_user():
    print(">>> Initializing Debug User...")
    payload = {"user_id": "debug_user_persistent", "text": "狀態"}
    try:
        resp = requests.post(DEBUG_ENDPOINT, json=payload, timeout=10)
        resp.raise_for_status()
        print(">>> User Initialized.")
    except Exception as e:
        print(f"FAILED TO INIT USER: {e}")


def get_real_user_id():
    print(">>> Fetching Real User ID from Cloud App...")
    payload = {"user_id": "debug_finder", "text": "/sys"}
    try:
        resp = requests.post(DEBUG_ENDPOINT, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        text = data.get("text", "")
        print(f"DEBUG /SYS RESPONSE: {text}")

        # Regex to find User ID: Sample User: Name (USER_ID)
        # Modified to be more permissive with whitespace
        match = re.search(r"Sample User: .+ \((U[0-9a-f]{32})\)", text)
        if match:
            uid = match.group(1)
            print(f">>> Found User ID: {uid}")
            return uid

        # Fallback: finding ANY user ID pattern in the text (maybe debug_user_persistent?)
        # debug_user_persistent is not a valid LINE ID (U+32 hex) so regex won't match it.
        # But if the Real User is there, it fits.
        # If only debug_user_persistent is there, we can't use it for Push (LINE Regex).

        return None

    except Exception as e:
        print(f"FAILED TO FETCH ID: {e}")
        return None


def trigger_webhook_bypass(user_id, command_text):
    print(f">>> Triggering Full Loop Webhook Test for '{command_text}'...")

    # Construct LINE Webhook Payload
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

    headers = {
        "Content-Type": "application/json",
        "X-Debug-Bypass": "true",
        "X-Line-Signature": "dummy_sig",  # Required even if ignored
    }

    try:
        resp = requests.post(WEBHOOK_ENDPOINT, json=webhook_body, headers=headers, timeout=10)
        print(f"Webhook Response: {resp.status_code}")
        print(f"Body: {resp.text}")

        if resp.status_code == 200:
            print(">>> SUCCESS: Webhook accepted. Check your LINE app for push message!")
            return True
        else:
            print(">>> FAILED: Webhook rejected.")
            return False

    except Exception as e:
        print(f"WEBHOOK REQUEST FAILED: {e}")
        return False


if __name__ == "__main__":
    initialize_user()
    uid = get_real_user_id()
    if uid:
        print("------------- TEST 1: STATUS -------------")
        # Use full test (Webhook -> Push) for Status
        trigger_webhook_bypass(uid, "狀態")

        print("\n------------- TEST 2: SHOP -------------")
        trigger_webhook_bypass(uid, "商店")
    else:
        print("Cannot proceed with Push Logic without Real User ID.")
        print("Falling back to dummy ID to verify Webhook connectivity only (Push will fail at Line Server).")
        trigger_webhook_bypass("Udeadbeefdeadbeefdeadbeefdeadbeef", "狀態")
