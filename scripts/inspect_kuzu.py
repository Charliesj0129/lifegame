import kuzu
import os

DB_PATH = "./data/lifegame_graph"

def inspect():
    if not os.path.exists(DB_PATH):
        print(f"DB Path {DB_PATH} does not exist.")
        return

    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)
    
    print("--- Nodes ---")
    try:
        # Kuzu internal tables or show tables command?
        # CALL SHOW_TABLES() return name, type, ...
        results = conn.execute("CALL SHOW_TABLES() RETURN *")
        while results.has_next():
            print(results.get_next())
    except Exception as e:
        print(f"Error showing tables: {e}")

if __name__ == "__main__":
    inspect()
