import kuzu
import shutil
import os
import logging

# Configure logging to see what happens
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_kuzu")

DB_PATH = "./debug_kuzu_db"

def test_init():
    if os.path.exists(DB_PATH):
        shutil.rmtree(DB_PATH)
    
    logger.info(f"Creating DB at {DB_PATH}")
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)
    
    logger.info("Checking if User table exists (expecting failure)...")
    try:
        conn.execute("MATCH (u:User) RETURN count(u) LIMIT 1")
        logger.info(">>> SUCCESS: User table somehow exists?")
    except RuntimeError as e:
        logger.info(f">>> CAUGHT RuntimeError: {e}")
        logger.info("Initializing Schema...")
        try:
            conn.execute("CREATE NODE TABLE User(name STRING, PRIMARY KEY (name))")
            logger.info("Created User")
            conn.execute("CREATE NODE TABLE NPC(name STRING, role STRING, mood STRING, PRIMARY KEY (name))")
            logger.info("Created NPC")
        except Exception as e_inner:
            logger.error(f"Failed inside creation block: {e_inner}")
    except Exception as e_other:
         logger.info(f">>> CAUGHT Other Exception type: {type(e_other)} - {e_other}")

    # Verify tables
    logger.info("Verifying tables...")
    try:
        headers = conn.execute("CALL SHOW_TABLES() RETURN *").get_next()
        logger.info(f"Show Tables Result: {headers}") # Wait, get_next returns a row
        
        # Proper iteration
        results = conn.execute("CALL SHOW_TABLES() RETURN *")
        while results.has_next():
            print("Table:", results.get_next())
            
    except Exception as e:
        logger.error(f"Verification failed: {e}")

if __name__ == "__main__":
    test_init()
