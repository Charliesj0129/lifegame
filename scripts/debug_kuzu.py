import kuzu
import shutil
import os

DB_PATH = "./test_kuzu_debug_dir"

def test_kuzu():
    if os.path.exists(DB_PATH):
        shutil.rmtree(DB_PATH)
            
    print(f"Testing path: {DB_PATH}")
    os.makedirs(DB_PATH)
    print("Directory created.")
    
    try:
        print("1. Init Kuzu (Path exists as Directory)")
        kuzu.Database(DB_PATH)
        print("SUCCESS")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_kuzu()
