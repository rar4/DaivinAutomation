import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path="daivin.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self):
        """Initializes the database and creates the required tables."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Users Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        age INTEGER,
                        name TEXT,
                        last_name TEXT,
                        bio TEXT,
                        photos BLOB
                    )
                """)

                # 2. Interests Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS interests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        interest TEXT UNIQUE
                    )
                """)

                # 3. Analysis Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS analysis (
                        user_id INTEGER,
                        model_name TEXT,
                        prompt_path TEXT,
                        match_score REAL,
                        profile_summary TEXT,
                        interest_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        opener TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        FOREIGN KEY (interest_id) REFERENCES interests (id)
                    )
                """)
                
                conn.commit()
                logger.info("Database initialized successfully.")
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {e}")

    def save_user(self, age: int , name: str,  summary, photos=None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (age, name, summary, photos) VALUES (?, ?, ?, ?, ?)",
                    (age, name, summary, photos)
                )
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error saving user: {e}")
            return None

    def save_interest(self, interest_text):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO interests (interest) VALUES (?)", (interest_text,))
                cursor.execute("SELECT id FROM interests WHERE interest = ?", (interest_text,))
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Error saving interest: {e}")
            return None

    def save_analysis(self, user_id, model_name, prompt_path, match_score, profile_summary, interest_id, opener):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO analysis (user_id, model_name, prompt_path, match_score, profile_summary, interest_id, opener)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, model_name, prompt_path, match_score, profile_summary, interest_id, opener)
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error saving analysis: {e}")