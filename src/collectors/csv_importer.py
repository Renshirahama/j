from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_COLUMNS = ["date", "machine_name", "machine_number", "games", "bb", "rb", "difference_medals"]
OPTIONAL_COLUMNS = [
    "combined_probability",
    "bb_probability",
    "rb_probability",
    "store_total_difference",
    "store_average_difference",
    "store_average_games",
    "store_win_rate",
]


def read_csv(path: str | Path, store: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in BASE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")
    df = df.copy()
    df["store"] = store
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["machine_number"] = df["machine_number"].astype(str)
    for col in ["games", "bb", "rb", "difference_medals"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[["date", "store", *BASE_COLUMNS[1:], *OPTIONAL_COLUMNS]]
