import json
import sys
from datetime import datetime

import requests

BASE_URL = "https://app-lifgame-2026.azurewebsites.net/debug/execute"
USER_ID = "debug_user_verify_001"

TEST_COMMANDS = [
    ("Status", "狀態"),
    ("Quests", "任務"),
    ("Checkin", "簽到"),
    ("Inventory", "背包"),
    ("Shop", "商店"),
    ("NewGoal", "我想設定我要成為健身房常客"),
    ("SysInfo", "/sys"),  # Also verify sys info works
    ("HealthCheck", "/health"),  # This hits the other endpoint, but good to note
    ("ManualMigrate", "/migrate"),  # This takes longer, but let's try
]


def run_verify():
    print(f"[{datetime.now()}] Starting Verification Sequence on {BASE_URL}")
    print("-" * 50)

    success_count = 0
    fail_count = 0

    for name, cmd_text in TEST_COMMANDS:
        if name == "HealthCheck":
            # DIFFERENT ENDPOINT
            continue

        print(f"Testing Command: {cmd_text} ({name})... ", end="")
        sys.stdout.flush()

        try:
            resp = requests.post(BASE_URL, json={"user_id": USER_ID, "text": cmd_text}, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if "error" in data:
                    print(f"FAIL (App Error): {data}")
                    fail_count += 1
                else:
                    preview = data.get("text", "")[:100].replace("\n", " ")
                    print(f"PASS. Response: {preview}...")
                    success_count += 1
            else:
                print(f"FAIL (HTTP {resp.status_code}): {resp.text}")
                fail_count += 1
        except Exception as e:
            print(f"FAIL (Exception): {e}")
            fail_count += 1

    print("-" * 50)
    print(f"Verification Check Complete: {success_count} Passed, {fail_count} Failed.")


if __name__ == "__main__":
    run_verify()
