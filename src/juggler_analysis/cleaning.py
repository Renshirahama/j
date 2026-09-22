from __future__ import annotations

import pandas as pd


def valid_results_mask(df: pd.DataFrame) -> pd.Series:
    """Return rows safe to use for ranking and backtesting.

    Invalid rows are kept in the source database for auditability, but must not
    influence rolling features, probabilities, or backtests.
    """
    required = ["date", "store", "machine_name", "machine_number", "games", "bb", "rb", "difference_medals"]
    if not set(required).issubset(df.columns):
        return pd.Series(False, index=df.index)
    games = pd.to_numeric(df["games"], errors="coerce")
    bb = pd.to_numeric(df["bb"], errors="coerce")
    rb = pd.to_numeric(df["rb"], errors="coerce")
    text_ok = df[["store", "machine_name", "machine_number"]].notna().all(axis=1)
    text_ok &= df["store"].astype(str).str.strip().ne("")
    text_ok &= df["machine_name"].astype(str).str.strip().ne("")
    text_ok &= df["machine_number"].astype(str).str.strip().ne("")
    return text_ok & games.notna() & games.ge(1) & bb.notna() & bb.ge(0) & rb.notna() & rb.ge(0) & bb.add(rb).le(games)


def filter_valid_results(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[valid_results_mask(df)].copy()


def coverage_summary(df: pd.DataFrame) -> dict[str, object]:
    """Summarize observed dates and unusually sparse collection days.

    Calendar-day coverage is intentionally reported as a diagnostic only:
    stores may be closed on some days, so missing dates are never filled with
    zeroes or treated as losses.
    """
    if df.empty or "date" not in df.columns:
        return {
            "observed_days": 0,
            "first_date": None,
            "last_date": None,
            "calendar_span_days": 0,
            "missing_calendar_days": 0,
            "gap_dates": [],
            "median_rows_per_day": 0,
            "sparse_days": [],
        }
    dates = sorted(pd.to_datetime(df["date"]).dt.date.unique())
    first_date, last_date = dates[0], dates[-1]
    span = (last_date - first_date).days + 1
    date_set = set(dates)
    gap_dates = [str(first_date + pd.Timedelta(days=i)) for i in range(span) if first_date + pd.Timedelta(days=i) not in date_set]
    daily = df.assign(_date=pd.to_datetime(df["date"]).dt.date).groupby("_date").size()
    median_rows = float(daily.median())
    sparse_threshold = max(1.0, median_rows * 0.8)
    sparse_days = [str(d) for d, count in daily.items() if count < sparse_threshold]
    return {
        "observed_days": len(dates),
        "first_date": str(first_date),
        "last_date": str(last_date),
        "calendar_span_days": span,
        "missing_calendar_days": len(gap_dates),
        "gap_dates": gap_dates[:30],
        "median_rows_per_day": int(round(median_rows)),
        "sparse_days": sparse_days[:30],
    }


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
