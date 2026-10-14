import os
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@contextmanager
def get_connection(database_url: str | None = None):
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required. Copy .env.example to .env.")
    connection = psycopg2.connect(url, connect_timeout=5)
    try:
        # Commit on success and roll back on failure.
        with connection:
            yield connection
    finally:
        # psycopg2's connection context does not close the connection itself.
        connection.close()
