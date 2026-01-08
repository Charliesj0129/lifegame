import sqlite3
import os

DB_PATH = "data/game.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(quests)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "meta" in columns:
            print("Column 'meta' already exists in 'quests'.")
        else:
            print("Adding 'meta' column to 'quests'...")
            cursor.execute("ALTER TABLE quests ADD COLUMN meta JSON")
            conn.commit()
            print("Migration successful.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
