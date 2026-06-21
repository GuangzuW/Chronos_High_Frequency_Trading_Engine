"""SQLite persistence (Phase 1 durability) — one database, multiple domain tables.

A single `Database` owns the connection (thread-safe via a lock + check_same_thread=False,
so it works under the threaded HTTP server) and exposes typed methods for each bounded
context. The ledger persists its append-only journal (the event log — balances are a replay
projection) plus active buying-power holds; the OMS persists orders; the portfolio persists
positions. On startup each component replays its tables to rebuild in-memory state.

Reference data is treated as configuration (re-seeded at boot from a master), not user
state, so it is intentionally not persisted here.
"""

from __future__ import annotations

import json
import sqlite3
import threading

_SCHEMA = """
CREATE TABLE IF NOT EXISTS journal (
    seq    INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_id TEXT UNIQUE NOT NULL,
    legs   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS holds (
    hold_id TEXT PRIMARY KEY,
    account TEXT NOT NULL,
    amount  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
    id            INTEGER PRIMARY KEY,
    account       TEXT, symbol TEXT, side TEXT,
    price         INTEGER, qty INTEGER,
    status        TEXT, filled INTEGER, reject_reason TEXT,
    tif           TEXT, order_type TEXT, stop_price INTEGER
);
CREATE TABLE IF NOT EXISTS positions (
    account        TEXT, symbol TEXT,
    qty            INTEGER, cost_cents INTEGER, realized_cents INTEGER,
    PRIMARY KEY (account, symbol)
);
CREATE TABLE IF NOT EXISTS trades (
    seq           INTEGER PRIMARY KEY,
    symbol        TEXT, buy_order_id INTEGER, sell_order_id INTEGER,
    buyer         TEXT, seller TEXT, price INTEGER, qty INTEGER, ts_ns INTEGER
);
"""


class Database:
    def __init__(self, path: str) -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ---- ledger journal ----
    def append_journal(self, txn_id: str, legs: list[tuple[str, int]]) -> None:
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO journal(txn_id, legs) VALUES(?, ?)",
                               (txn_id, json.dumps(legs)))

    def load_journal(self) -> list[tuple[str, list[tuple[str, int]]]]:
        with self._lock:
            rows = self._conn.execute("SELECT txn_id, legs FROM journal ORDER BY seq").fetchall()
        return [(txn_id, [tuple(leg) for leg in json.loads(legs)]) for txn_id, legs in rows]

    # ---- ledger holds ----
    def save_hold(self, hold_id: str, account: str, amount: int) -> None:
        with self._lock, self._conn:
            self._conn.execute("INSERT OR REPLACE INTO holds(hold_id, account, amount) VALUES(?, ?, ?)",
                               (hold_id, account, amount))

    def delete_hold(self, hold_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM holds WHERE hold_id = ?", (hold_id,))

    def load_holds(self) -> dict[str, tuple[str, int]]:
        with self._lock:
            rows = self._conn.execute("SELECT hold_id, account, amount FROM holds").fetchall()
        return {hold_id: (account, amount) for hold_id, account, amount in rows}

    # ---- OMS orders ----
    def save_order(self, fields: tuple) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO orders"
                "(id, account, symbol, side, price, qty, status, filled, reject_reason,"
                " tif, order_type, stop_price)"
                " VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", fields)

    def load_orders(self) -> list[tuple]:
        with self._lock:
            return self._conn.execute(
                "SELECT id, account, symbol, side, price, qty, status, filled, reject_reason,"
                " tif, order_type, stop_price FROM orders ORDER BY id").fetchall()

    # ---- portfolio positions ----
    def save_position(self, account: str, symbol: str, qty: int,
                      cost_cents: int, realized_cents: int) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO positions"
                "(account, symbol, qty, cost_cents, realized_cents) VALUES(?, ?, ?, ?, ?)",
                (account, symbol, qty, cost_cents, realized_cents))

    def load_positions(self) -> list[tuple]:
        with self._lock:
            return self._conn.execute(
                "SELECT account, symbol, qty, cost_cents, realized_cents FROM positions").fetchall()

    # ---- trade history ----
    def save_trade(self, fields: tuple) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO trades"
                "(seq, symbol, buy_order_id, sell_order_id, buyer, seller, price, qty, ts_ns)"
                " VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", fields)

    def load_trades(self) -> list[tuple]:
        with self._lock:
            return self._conn.execute(
                "SELECT seq, symbol, buy_order_id, sell_order_id, buyer, seller, price, qty, ts_ns"
                " FROM trades ORDER BY seq").fetchall()
