import zipfile
import os
import sys


def inspect_logs(zip_path):
    if not os.path.exists(zip_path):
        print(f"File not found: {zip_path}")
        return

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            print(f" inspecting {zip_path}...")
            for filename in z.namelist():
                if filename.endswith(".log") or filename.endswith(".txt"):
                    with z.open(filename) as f:
                        content = f.read().decode("utf-8", errors="ignore")
                        lines = content.split("\n")
                        # Filter for errors or specific keywords
                        error_lines = [
                            line for line in lines if "ERROR" in line or "Exception" in line or "Traceback" in line
                        ]
                        if error_lines:
                            print(f"\n--- {filename} ---")
                            # Contextual print
                            for i, line in enumerate(lines):
                                if "ERROR" in line or "Exception" in line:
                                    start = max(0, i - 5)
                                    end = min(len(lines), i + 10)
                                    print(f"--- Line {i} ---")
                                    print("\n".join(lines[start:end]))
                        else:
                            # Print last few lines anyway to see activity
                            pass
    except Exception as e:
        print(f"Failed to read zip: {e}")


if __name__ == "__main__":
    inspect_logs("debug_silent.zip")
