"""
Configuration Module
Reads MySQL connection settings from environment variables or a local .env file.
"""

import os

base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, "..", ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(base_dir, ".env")

if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip("'\"")

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "dbos_ev")

