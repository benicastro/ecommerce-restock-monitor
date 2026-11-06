import sqlite3
from contextlib import contextmanager
from pathlib import Path


DATABASE_FILE = Path("monitor.db")


@contextmanager
def get_connection():
    """Yield a transactional SQLite connection and always close it.

    sqlite3.Connection's own context manager commits or rolls back,
    but does NOT close the connection on exit. Explicit closure is
    needed to avoid WinError 32 when tests remove temporary databases.
    """
    connection = sqlite3.connect(DATABASE_FILE)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS product_state (
                product_key TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                shop_id TEXT,
                item_id TEXT,
                title TEXT,
                available INTEGER NOT NULL,
                price REAL,
                updated_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS product_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_key TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT,
                price REAL,
                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS monitor_health (
                product_key TEXT PRIMARY KEY,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                alert_sent INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )

        connection.commit()
