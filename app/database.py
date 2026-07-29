import sqlite3

DATABASE_NAME = "tasks.db"


def get_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]

    if count == 0:
        sample_tasks = [
            ("Learn FastAPI", 0),
            ("Finish Assignment", 0),
            ("Push to GitHub", 1)
        ]

        cursor.executemany(
            "INSERT INTO tasks(title, done) VALUES (?, ?)",
            sample_tasks
        )

    conn.commit()
    conn.close()