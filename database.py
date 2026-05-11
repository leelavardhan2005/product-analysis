import sqlite3
import json
import os
from typing import Optional, Dict

DB_PATH = 'users.db'

def get_conn():
    # Adding timeout and WAL mode strictly prevents "database is locked" errors permanently.
    conn = sqlite3.connect(DB_PATH, timeout=15.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def init_db():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_setup_complete BOOLEAN NOT NULL DEFAULT 0,
                profile_json TEXT
            )
        ''')
        conn.commit()
    finally:
        conn.close()

def create_user(user_id: str, username: str, password: str) -> bool:
    try:
        conn = get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (id, username, password, is_setup_complete) VALUES (?, ?, ?, ?)", (user_id, username, password, False))
            conn.commit()
            return True
        finally:
            conn.close()
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"DB Error: {e}")
        return False

def get_user_by_username(username: str) -> Optional[Dict]:
    conn = get_conn()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()

def update_user_profile(user_id: str, profile_dict: dict):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        json_str = json.dumps(profile_dict)
        cursor.execute("UPDATE users SET profile_json = ?, is_setup_complete = ? WHERE id = ?", (json_str, True, user_id))
        conn.commit()
    finally:
        conn.close()

def get_user_profile(user_id: str) -> Optional[Dict]:
    conn = get_conn()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT profile_json FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row['profile_json']:
            return json.loads(row['profile_json'])
        return None
    finally:
        conn.close()

init_db()
