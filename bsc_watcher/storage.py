import sqlite3
import time
from typing import Optional, List, Tuple, Set


class Storage:
    """Local SQLite store for syncing state and tracking discovered pairs."""

    def __init__(self, db_path: str = "watcher.db"):
        self.db_path = db_path
        self._conn = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, timeout=15.0)
            self._conn.row_factory = sqlite3.Row
            # enable WAL to avoid lock contention when background watcher queries
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
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
                    token0_symbol TEXT,
                    token1_symbol TEXT,
                    block_number INTEGER NOT NULL,
                    tx_hash TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS liquidity_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair_address TEXT NOT NULL,
                    reserve0 TEXT NOT NULL,
                    reserve1 TEXT NOT NULL,
                    block_number INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    FOREIGN KEY(pair_address) REFERENCES pairs(pair_address)
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS blacklist (
                    address TEXT PRIMARY KEY,
                    reason TEXT,
                    added_at REAL NOT NULL
                )
            """)
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_pairs_block ON pairs(block_number)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_liq_pair ON liquidity_events(pair_address)")

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

    def save_pair(
        self,
        pair: str,
        token0: str,
        token1: str,
        block: int,
        tx_hash: str,
        token0_sym: Optional[str] = None,
        token1_sym: Optional[str] = None
    ):
        now = time.time()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO pairs
                (pair_address, token0, token1, token0_symbol, token1_symbol, block_number, tx_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (pair.lower(), token0.lower(), token1.lower(), token0_sym, token1_sym, block, tx_hash, now)
            )

    def record_liquidity(self, pair: str, reserve0: int, reserve1: int, block: int):
        now = time.time()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO liquidity_events (pair_address, reserve0, reserve1, block_number, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (pair.lower(), str(reserve0), str(reserve1), block, now)
            )

    def has_pair(self, pair: str) -> bool:
        cur = self.connect().cursor()
        cur.execute("SELECT 1 FROM pairs WHERE pair_address = ?", (pair.lower(),))
        return cur.fetchone() is not None

    def load_blacklist(self) -> Set[str]:
        cur = self.connect().cursor()
        cur.execute("SELECT address FROM blacklist")
        return {row["address"].lower() for row in cur.fetchall()}

    def add_blacklist(self, address: str, reason: str = "scam"):
        with self.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO blacklist (address, reason, added_at) VALUES (?, ?, ?)",
                (address.lower(), reason, time.time())
            )

    def get_recent_pairs(self, limit: int = 20) -> List[dict]:
        cur = self.connect().cursor()
        cur.execute(
            """
            SELECT pair_address, token0, token1, token0_symbol, token1_symbol, block_number, tx_hash, created_at
            FROM pairs ORDER BY created_at DESC LIMIT ?
            """,
            (limit,)
        )
        return [dict(row) for row in cur.fetchall()]

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
