import sqlite3


class Database:
    def __init__(self, db_name="scores.db"):
        self.db_path = db_name

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def save_score(self, login: str, score: int):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (login, score) VALUES (?, ?)", (login, score)
            )
            conn.commit()
        finally:
            conn.close()

    def get_all_scores(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            return cursor.fetchall()
        finally:
            conn.close()

    def init_table(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login TEXT NOT NULL,
                    score INTEGER NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()
