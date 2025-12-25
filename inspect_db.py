import sqlite3

def inspect():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    print("--- Table Info ---")
    c.execute("PRAGMA table_info(reports);")
    columns = [row['name'] for row in c.fetchall()]
    print(columns)
    
    print("\n--- Reports ---")
    c.execute("SELECT id, location_name, latitude, longitude, status, description FROM reports")
    for row in c.fetchall():
        print(dict(row))
        
    conn.close()

if __name__ == "__main__":
    inspect()
