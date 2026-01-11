import os

files_to_update = [
    "tests/unit/test_context_service.py",
    "tests/unit/test_phase4_graph.py",
    "tests/unit/test_flow_controller.py",
    "tests/unit/test_phase5_perception.py",
    "tests/unit/test_brain_service.py",
    "legacy/services/user_service.py",
    "tests/integration/test_full_flow.py",
    "tests/integration/test_ha_webhook.py",
    "tests/integration/test_brain_hook.py",
    "app/api/nerves.py",
    "application/services/brain_service.py",
    "application/services/perception_service.py",
]

for filepath in files_to_update:
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            content = f.read()

        new_content = content.replace("app.services", "application.services")

        if content != new_content:
            with open(filepath, "w") as f:
                f.write(new_content)
            print(f"Updated {filepath}")
    else:
        print(f"Skipped {filepath} (not found)")
