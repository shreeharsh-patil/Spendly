import sqlite3
import os
from flask import g

DATABASE = os.path.join(os.path.dirname(__file__), 'spendly.db')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def init_db():
    db = get_db()
    
    # Create Users Table
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            monthly_budget REAL DEFAULT 10000.0,
            phone TEXT,
            avatar_url TEXT
        )
    """)

    
    # Create Expenses Table
    db.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    db.commit()

def seed_db():
    # Optional: Add sample data for development if needed
    pass
