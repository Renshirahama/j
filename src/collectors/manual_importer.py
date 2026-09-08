from __future__ import annotations

from io import StringIO

import pandas as pd

from .csv_importer import read_csv


def read_pasted_table(text: str, store: str) -> pd.DataFrame:
    sep = "\t" if "\t" in text.splitlines()[0] else ","
    buf = StringIO(text.strip())
    tmp = pd.read_csv(buf, sep=sep)
    path_like = StringIO(tmp.to_csv(index=False))
    df = pd.read_csv(path_like)
    # Reuse normalization without touching disk.
    missing = [c for c in ["date", "machine_name", "machine_number", "games", "bb", "rb", "difference_medals"] if c not in df.columns]
    if missing:
        raise ValueError(f"pasted table missing required columns: {missing}")
    df["store"] = store
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["machine_number"] = df["machine_number"].astype(str)
    for col in ["games", "bb", "rb", "difference_medals"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df
