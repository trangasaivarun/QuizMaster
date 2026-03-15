import sqlite3
import os

# Script to initialize the SQLite database using the schema.sql file

DB_FILE = os.path.join(os.path.dirname(__file__), 'quizmaster.db')
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), 'schema.sql')

def init_db():
    print(f"Initializing database from {SCHEMA_FILE}...")
    
    # Check if schema file exists
    if not os.path.exists(SCHEMA_FILE):
        print(f"Error: Schema file '{SCHEMA_FILE}' not found.")
        return
        
    try:
        # Create a new connection to the database (creates file if it doesn't exist)
        conn = sqlite3.connect(DB_FILE)
        
        # Open and read the schema file
        with open(SCHEMA_FILE, 'r') as f:
            schema_script = f.read()
            
        # Execute the script
        cursor = conn.cursor()
        cursor.executescript(schema_script)
        
        # Insert default admin if it doesn't exist (executescript handles IGNORE differently in some SQLite builds, better to be explicit)
        cursor.execute("SELECT id FROM admins WHERE email = 'admin@quizmaster.com'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO admins (email, password) VALUES ('admin@quizmaster.com', 'admin123')")
            
        conn.commit()
        print(f"Database setup complete. File created: {DB_FILE}")
        
    except sqlite3.Error as e:
        print(f"An SQLite error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    init_db()
