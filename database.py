import sqlite3
import json
from datetime import datetime


class Database:
    def __init__(self, db_file='database.db'):
        self.connection = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                subscribed INTEGER DEFAULT 0,
                created_at TIMESTAMP
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                order_type TEXT,
                amount REAL,
                price REAL,
                recipient TEXT,
                status TEXT DEFAULT 'pending',
                payment_method TEXT,
                invoice_id TEXT,
                created_at TIMESTAMP
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_data (
                user_id INTEGER PRIMARY KEY,
                star_value INTEGER,
                ton_address TEXT,
                ton_value REAL,
                period TEXT,
                priceprem REAL,
                temp_username TEXT
            )
        ''')

        self.connection.commit()

    def add_user(self, user_id, username):
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, created_at)
            VALUES (?, ?, ?)
        ''', (user_id, username, datetime.now()))
        self.connection.commit()

    def update_subscription(self, user_id, subscribed):
        self.cursor.execute('''
            UPDATE users SET subscribed = ? WHERE user_id = ?
        ''', (subscribed, user_id))
        self.connection.commit()

    def is_subscribed(self, user_id):
        self.cursor.execute('SELECT subscribed FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def save_temp_data(self, user_id, **kwargs):
        columns = ', '.join(kwargs.keys())
        placeholders = ', '.join(['?'] * len(kwargs))
        values = list(kwargs.values())

        self.cursor.execute(f'''
            INSERT OR REPLACE INTO user_data (user_id, {columns})
            VALUES (?, {placeholders})
        ''', (user_id, *values))
        self.connection.commit()

    def get_temp_data(self, user_id):
        self.cursor.execute('SELECT * FROM user_data WHERE user_id = ?', (user_id,))
        columns = [description[0] for description in self.cursor.description]
        row = self.cursor.fetchone()
        return dict(zip(columns, row)) if row else {}

    def create_order(self, user_id, order_type, amount, price, recipient=None):
        self.cursor.execute('''
            INSERT INTO orders (user_id, order_type, amount, price, recipient, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, order_type, amount, price, recipient, datetime.now()))
        self.connection.commit()
        return self.cursor.lastrowid


db = Database()
