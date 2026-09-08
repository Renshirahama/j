from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_machine_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  store TEXT NOT NULL,
  machine_name TEXT NOT NULL,
  machine_number TEXT NOT NULL,
  games INTEGER NOT NULL,
  bb INTEGER NOT NULL,
  rb INTEGER NOT NULL,
  difference_medals INTEGER NOT NULL,
  combined_probability REAL,
  bb_probability REAL,
  rb_probability REAL,
  store_total_difference REAL,
  store_average_difference REAL,
  store_average_games REAL,
  store_win_rate REAL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(date, store, machine_name, machine_number)
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(SCHEMA)
    return conn


def upsert_results(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    cols = [
        "date",
        "store",
        "machine_name",
        "machine_number",
        "games",
        "bb",
        "rb",
        "difference_medals",
        "combined_probability",
        "bb_probability",
        "rb_probability",
        "store_total_difference",
        "store_average_difference",
        "store_average_games",
        "store_win_rate",
    ]
    rows = df.reindex(columns=cols).where(pd.notnull(df), None).to_records(index=False).tolist()
    before = conn.total_changes
    placeholders = ",".join(["?"] * len(cols))
    updates = ",".join([f"{c}=excluded.{c}" for c in cols if c not in {"date", "store", "machine_name", "machine_number"}])
    conn.executemany(
        f"""
        INSERT INTO daily_machine_results ({",".join(cols)})
        VALUES ({placeholders})
        ON CONFLICT(date, store, machine_name, machine_number)
        DO UPDATE SET {updates}
        """,
        rows,
    )
    conn.commit()
    return conn.total_changes - before


def load_results(conn: sqlite3.Connection, store: str | None = None, machine_name: str | None = None) -> pd.DataFrame:
    query = "SELECT * FROM daily_machine_results"
    params: list[str] = []
    where: list[str] = []
    if store:
        where.append("store = ?")
        params.append(store)
    if machine_name:
        where.append("machine_name = ?")
        params.append(machine_name)
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY date, machine_number"
    df = pd.read_sql_query(query, conn, params=params)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["machine_number"] = df["machine_number"].astype(str)
    return df
