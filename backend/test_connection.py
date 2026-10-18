"""
Database Connection Test
Simple script to verify that Python connects to the dbos_ev MySQL database.
"""

import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from config import DB_HOST, DB_PORT, DB_USER, DB_NAME
from db import get_connection, execute_select


def main():
    print("=" * 55)
    print("Testing MySQL Database Connection")
    print("=" * 55)
    print(f"Host:     {DB_HOST}:{DB_PORT}")
    print(f"Database: {DB_NAME}")
    print(f"User:     {DB_USER}")
    print("-" * 55)

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        print(f"[PASS] Connected to MySQL successfully! Version: {version}")
    except Exception as e:
        print(f"[FAIL] Could not connect to MySQL: {e}")
        return False

    try:
        users = execute_select(
            "SELECT user_id, username, email FROM APP_USER WHERE user_id = %s",
            (1,)
        )
        if users:
            print(f"[PASS] Parameterized query worked! Found user: {users[0]['username']}")
        else:
            print("[PASS] Parameterized query worked! (Table APP_USER has no row with user_id = 1)")
    except Exception as e:
        print(f"[FAIL] Query test failed: {e}")
        return False

    try:
        tables = execute_select(
            "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s",
            (DB_NAME,)
        )
        table_names = [row["TABLE_NAME"] for row in tables]
        print(f"[PASS] Verified {len(table_names)} tables in '{DB_NAME}':")
        print("      ", ", ".join(table_names))
    except Exception as e:
        print(f"[FAIL] Could not list tables: {e}")
        return False

    print("=" * 55)
    print("All connection tests passed successfully!")
    print("=" * 55)
    return True


if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
