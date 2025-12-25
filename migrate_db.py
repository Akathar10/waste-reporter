import sqlite3
import datetime

def migrate():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # 1. Delete the bad report
    print("Deleting report 0eb0e06a...")
    c.execute("DELETE FROM reports WHERE id='0eb0e06a'")
    if c.rowcount > 0:
        print("Report 0eb0e06a deleted.")
    else:
        print("Report 0eb0e06a not found (already deleted?).")

    # 2. Add updated_at column
    print("Checking for updated_at column...")
    try:
        c.execute("ALTER TABLE reports ADD COLUMN updated_at TIMESTAMP")
        print("Column 'updated_at' added successfully.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'updated_at' already exists.")
        else:
            print(f"Error adding column: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
