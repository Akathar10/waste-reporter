import sqlite3
from datetime import datetime, timedelta
import requests
import json
import time

# Use local request if server running, or simulate logic?
# Since we changed app.py, we rely on the running server to pick up changes (if auto-reload works).
# But we can also import app and test function directly to avoid server dependency.
# importing app might be risky if it starts server on import (it doesn't, hidden in __name__ == main).

from app import get_reports, app

def test_expiry():
    with app.app_context():
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # 1. Clear test data if any
        c.execute("DELETE FROM reports WHERE id LIKE 'test_%'")
        
        now = datetime.now()
        old = now - timedelta(hours=25)
        fresh = now - timedelta(hours=1)
        
        # 2. Insert Test Reports
        # A: Resolved Old (Should be hidden)
        c.execute("INSERT INTO reports (id, status, updated_at, description) VALUES (?, ?, ?, ?)",
                  ('test_old', 'Resolved', str(old), 'Should be hidden'))
        
        # B: Resolved Fresh (Should be visible)
        c.execute("INSERT INTO reports (id, status, updated_at, description) VALUES (?, ?, ?, ?)",
                  ('test_fresh', 'Resolved', str(fresh), 'Should be visible'))
        
        # C: Pending (Should be visible)
        c.execute("INSERT INTO reports (id, status, description) VALUES (?, ?, ?)",
                  ('test_pending', 'Pending', 'Should be visible'))

        conn.commit()
        conn.close()
        
        # 3. Call API function directly
        # Note: get_reports returns a Response object in Flask
        response = get_reports()
        data = response.get_json()
        
        ids = [r['id'] for r in data]
        print(f"Visible IDs: {ids}")
        
        if 'test_old' in ids:
            print("FAIL: test_old is visible")
        else:
            print("PASS: test_old is hidden")
            
        if 'test_fresh' in ids:
            print("PASS: test_fresh is visible")
        else:
            print("FAIL: test_fresh is hidden")
            
        if 'test_pending' in ids:
            print("PASS: test_pending is visible")
        else:
            print("FAIL: test_pending is hidden")
            
        # Cleanup
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("DELETE FROM reports WHERE id LIKE 'test_%'")
        conn.commit()
        conn.close()

if __name__ == "__main__":
    test_expiry()
