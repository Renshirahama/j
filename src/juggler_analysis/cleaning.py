from __future__ import annotations

import pandas as pd


def quality_report(df: pd.DataFrame) -> pd.DataFrame:
    issues: list[dict[str, object]] = []
    key_cols = ["date", "store", "machine_name", "machine_number"]
    dupes = df[df.duplicated(key_cols, keep=False)] if set(key_cols).issubset(df.columns) else pd.DataFrame()
    for idx, row in df.iterrows():
        row_issues: list[str] = []
        if pd.isna(row.get("games")) or int(row.get("games", 0)) == 0:
            row_issues.append("games_zero_or_missing")
        if pd.isna(row.get("bb")) or int(row.get("bb", 0)) < 0:
            row_issues.append("bb_negative_or_missing")
        if pd.isna(row.get("rb")) or int(row.get("rb", 0)) < 0:
            row_issues.append("rb_negative_or_missing")
        games = 0 if pd.isna(row.get("games")) else int(row.get("games"))
        bb = 0 if pd.isna(row.get("bb")) else int(row.get("bb"))
        rb = 0 if pd.isna(row.get("rb")) else int(row.get("rb"))
        if bb + rb > games:
            row_issues.append("bonus_count_exceeds_games")
        if not dupes.empty and idx in dupes.index:
            row_issues.append("duplicate_same_day_machine")
        for issue in row_issues:
            issues.append(
                {
                    "row_index": idx,
                    "issue": issue,
                    "date": row.get("date"),
                    "machine_number": row.get("machine_number"),
                    "value": row.to_dict(),
                }
            )
    return pd.DataFrame(issues)


def normalize_probabilities(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["combined_probability"] = out["games"] / (out["bb"] + out["rb"]).replace(0, pd.NA)
    out["bb_probability"] = out["games"] / out["bb"].replace(0, pd.NA)
    out["rb_probability"] = out["games"] / out["rb"].replace(0, pd.NA)
    return out
