import os
import sqlite3


class Database:
    def __init__(self, db_name="scores.db"):
        self.db_path = os.path.join(os.path.dirname(__file__), db_name)
        self.connection = None

    def connect(self):
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT NOT NULL,
                score INTEGER NOT NULL
            )
        """)
        self.connection.commit()

    def save_score(self, login: str, score: int):
        cursor = self.connection.cursor()
        cursor.execute("INSERT INTO users (login, score) VALUES (?, ?)", (login, score))
        self.connection.commit()

    def get_all_scores(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users")
        return cursor.fetchall()

    def close(self):
        if self.connection:
            self.connection.close()
