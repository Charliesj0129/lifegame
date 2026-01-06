import json
import os
import sys
import urllib.request


REQUIRED_SECTIONS = ["Rollback Procedure", "Data Migration Notes"]
WATCH_PATHS = (
    "app/models/",
    "doc/PROMPTS",
    "app/alembic/versions/",
)


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("No GITHUB_EVENT_PATH found. Skipping PR checks.")
        return 0

    with open(event_path, "r", encoding="utf-8") as handle:
        event = json.load(handle)

    pr = event.get("pull_request")
    if not pr:
        print("No pull_request payload. Skipping PR checks.")
        return 0

    body = pr.get("body") or ""
    missing_sections = [
        section for section in REQUIRED_SECTIONS if section.lower() not in body.lower()
    ]

    files_url = pr.get("url", "") + "/files?per_page=100"
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        request = urllib.request.Request(files_url, headers=headers)
        with urllib.request.urlopen(request) as resp:
            files = json.load(resp)
    except Exception as exc:
        print(f"Failed to fetch PR files: {exc}")
        return 1

    touched = [
        f.get("filename", "")
        for f in files
        if f.get("filename")
    ]
    requires_sections = any(
        any(path.startswith(prefix) for prefix in WATCH_PATHS)
        for path in touched
    )

    if requires_sections and missing_sections:
        print("PR touches schema/models/prompts but required sections are missing.")
        for section in missing_sections:
            print(f"- Missing: {section}")
        return 1

    print("PR requirements check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
