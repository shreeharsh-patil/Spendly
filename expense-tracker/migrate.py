import sqlite3
import os

DATABASE = os.path.join(os.path.dirname(__file__), 'database', 'spendly.db')

def migrate():
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    
    # Try to add columns
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
        print("Added column 'phone'")
    except sqlite3.OperationalError as e:
        print(f"Skipping 'phone': {e}")
        
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
        print("Added column 'avatar_url'")
    except sqlite3.OperationalError as e:
        print(f"Skipping 'avatar_url': {e}")
        
    db.commit()
    db.close()

if __name__ == "__main__":
    migrate()
