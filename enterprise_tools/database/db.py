"""
db.py - SQLite connection and history table management
"""

import sqlite3
import os
import sys

# Detecta si está corriendo como ejecutable (PyInstaller)
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(__file__)

DB_PATH = os.path.join(base_path, 'enterprise_tools.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            file_name TEXT,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
