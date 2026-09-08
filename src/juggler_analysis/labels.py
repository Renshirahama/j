from __future__ import annotations

import pandas as pd


def apply_label(df: pd.DataFrame, label_config: dict, label_name: str) -> pd.Series:
    cfg = label_config["labels"][label_name]
    kind = cfg["type"]
    if kind == "diff_at_least":
        return df["difference_medals"] >= cfg["threshold"]
    if kind == "games_and_reg_probability":
        reg = df["games"] / df["rb"].replace(0, pd.NA)
        return (df["games"] >= cfg["min_games"]) & (reg <= cfg["max_reg_probability"])
    if kind == "games_combined_and_reg_probability":
        reg = df["games"] / df["rb"].replace(0, pd.NA)
        combined = df["games"] / (df["bb"] + df["rb"]).replace(0, pd.NA)
        return (df["games"] >= cfg["min_games"]) & (combined <= cfg["max_combined_probability"]) & (reg <= cfg["max_reg_probability"])
    if kind == "same_day_quantile":
        q = df.groupby(["date", "store", "machine_name"])["difference_medals"].transform(lambda s: s.quantile(cfg["quantile"]))
        return df["difference_medals"] >= q
    raise ValueError(f"Unknown label type: {kind}")
