import sqlite3
import time
from typing import Optional, List, Tuple


class Storage:
    """Local SQLite store for syncing state and tracking discovered pairs."""

    def __init__(self, db_path: str = "watcher.db"):
        self.db_path = db_path
        self._conn = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self.init_schema()
        return self._conn

    def init_schema(self):
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS pairs (
                    pair_address TEXT PRIMARY KEY,
                    token0 TEXT NOT NULL,
                    token1 TEXT NOT NULL,
                    block_number INTEGER NOT NULL,
                    tx_hash TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)

    def get_last_block(self) -> Optional[int]:
        cur = self.connect().cursor()
        cur.execute("SELECT value FROM metadata WHERE key = 'last_block'")
        row = cur.fetchone()
        if row and row["value"]:
            return int(row["value"])
        return None

    def set_last_block(self, block_number: int):
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES ('last_block', ?)",
                (str(block_number),)
            )

    def save_pair(self, pair: str, token0: str, token1: str, block: int, tx_hash: str):
        now = time.time()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO pairs (pair_address, token0, token1, block_number, tx_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (pair.lower(), token0.lower(), token1.lower(), block, tx_hash, now)
            )

    def has_pair(self, pair: str) -> bool:
        cur = self.connect().cursor()
        cur.execute("SELECT 1 FROM pairs WHERE pair_address = ?", (pair.lower(),))
        return cur.fetchone() is not None

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
