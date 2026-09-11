import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "cash.db"

CATEGORIES = [
    "предоплата",
    "акт",
    "подряд",
    "реклама",
    "сервисы",
    "налоги",
    "зарплата",
    "прочее",
]

ACCOUNTS = [
    ("tinkoff", "Тинькофф"),
    ("ip", "ИП"),
    ("taxes", "На налоги"),
]


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def init_db() -> None:
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            status TEXT NOT NULL CHECK(status IN ('plan', 'paid', 'overdue')),
            category TEXT NOT NULL,
            amount_rub INTEGER NOT NULL CHECK(amount_rub > 0),
            comment TEXT NOT NULL DEFAULT '',
            op_date TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            opening_balance INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_ops_date ON operations(op_date);
        CREATE INDEX IF NOT EXISTS idx_ops_status ON operations(status);
        """
    )

    for slug, name in ACCOUNTS:
        conn.execute(
            "INSERT OR IGNORE INTO accounts (slug, name, opening_balance) VALUES (?, ?, 0)",
            (slug, name),
        )

    columns = _column_names(conn, "operations")
    if "account_id" not in columns:
        conn.execute("ALTER TABLE operations ADD COLUMN account_id INTEGER")

    default_id = conn.execute("SELECT id FROM accounts WHERE slug = 'tinkoff'").fetchone()["id"]
    conn.execute("UPDATE operations SET account_id = ? WHERE account_id IS NULL", (default_id,))
    conn.commit()
    conn.close()
