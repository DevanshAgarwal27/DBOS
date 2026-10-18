"""
User Service Module
Handles registration and retrieval of users from the APP_USER table.
"""

import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from db import execute_select, execute_modify


def get_all_users():
    """
    Fetches all registered users from the database.
    """
    query = "SELECT user_id, username, email, phone_no FROM APP_USER ORDER BY user_id ASC;"
    return execute_select(query)


def display_users():
    """
    Prints all registered users in a clean, readable table format.
    """
    users = get_all_users()
    print("\n" + "=" * 75)
    print(f"{'ID':<6} | {'Username':<20} | {'Email':<30} | {'Phone':<15}")
    print("=" * 75)
    if not users:
        print("No users found in the database.")
    else:
        for u in users:
            print(f"{u['user_id']:<6} | {u['username']:<20} | {u['email']:<30} | {u['phone_no']:<15}")
    print("=" * 75 + "\n")


def register_user(username, email, phone_no):
    """
    Inserts a new user into APP_USER using parameterized SQL.
    If the user already exists, returns the existing user_id.
    Returns user_id on success, or None on failure.
    """
    check_query = "SELECT user_id, username FROM APP_USER WHERE username = %s OR email = %s;"
    existing = execute_select(check_query, (username, email))
    if existing:
        print(f"[INFO] User '{existing[0]['username']}' already registered (User ID: {existing[0]['user_id']}). Using existing user profile.")
        return existing[0]["user_id"]

    query = """
        INSERT INTO APP_USER (username, email, phone_no)
        VALUES (%s, %s, %s);
    """
    try:
        execute_modify(query, (username, email, phone_no))
        res = execute_select("SELECT user_id FROM APP_USER WHERE username = %s;", (username,))
        if res:
            return res[0]["user_id"]
        return None
    except Exception as e:
        print(f"[ERROR] Could not register user: {e}")
        return None


def create_user_interactive():
    """
    Prompts the user in the terminal to enter details and registers the user.
    Returns the new user_id if successful, or None.
    """
    print("\n--- Enter User Details ---")
    username = input("Enter username: ").strip()
    email = input("Enter email address: ").strip()
    phone_no = input("Enter phone number: ").strip()

    if not username or not email or not phone_no:
        print("[ERROR] All user fields (username, email, phone) are required.")
        return None

    user_id = register_user(username, email, phone_no)
    if user_id:
        print(f"[SUCCESS] User '{username}' registered successfully! (User ID: {user_id})")
        return user_id
    else:
        print("[FAILED] User registration failed. (Username or email might already exist).")
        return None

