from __future__ import annotations

import re
from datetime import date

import pandas as pd


def _prob(games: pd.Series, count: pd.Series) -> pd.Series:
    return games / count.replace(0, pd.NA)


def _last_digit(machine_number: object) -> int | None:
    digits = re.findall(r"\d", str(machine_number))
    return int(digits[-1]) if digits else None


def add_calendar_features(df: pd.DataFrame, special_config: dict) -> pd.DataFrame:
    out = df.copy()
    dt = pd.to_datetime(out["date"])
    out["weekday"] = dt.dt.weekday
    out["is_weekend"] = out["weekday"].isin([5, 6])
    out["day"] = dt.dt.day
    out["is_day_5"] = out["day"].isin(special_config["special_days"]["day_5"]["days"])
    out["is_day_7"] = out["day"].astype(str).str.contains(str(special_config["special_days"]["day_7"]["contains_digit"]))
    out["is_day_11"] = out["day"].isin(special_config["special_days"]["day_11"]["days"])
    out["is_day_22"] = out["day"].isin(special_config["special_days"]["day_22"]["days"])
    out["is_month_day_zorome"] = dt.dt.month.astype(str).str[-1] == dt.dt.day.astype(str).str[-1]
    return out


def add_base_metrics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().sort_values(["store", "machine_name", "machine_number", "date"])
    out["bb_probability_calc"] = _prob(out["games"], out["bb"])
    out["rb_probability_calc"] = _prob(out["games"], out["rb"])
    out["combined_probability_calc"] = _prob(out["games"], out["bb"] + out["rb"])
    out["diff_per_1000g"] = out["difference_medals"] / out["games"].replace(0, pd.NA) * 1000
    out["machine_last_digit"] = out["machine_number"].map(_last_digit)
    return out


def add_historical_features(df: pd.DataFrame) -> pd.DataFrame:
    out = add_base_metrics(df)
    group_cols = ["store", "machine_name", "machine_number"]
    out = out.sort_values([*group_cols, "date"])
    g = out.groupby(group_cols, group_keys=False)
    for window in [3, 7, 14, 30]:
        out[f"past_{window}d_avg_diff"] = g["difference_medals"].transform(lambda s: s.shift(1).rolling(window, min_periods=1).mean())
    for window in [3, 7, 14]:
        past_games = g["games"].transform(lambda s: s.shift(1).rolling(window, min_periods=1).sum())
        past_rb = g["rb"].transform(lambda s: s.shift(1).rolling(window, min_periods=1).sum())
        out[f"past_{window}d_reg_probability"] = _prob(past_games, past_rb)
    out["past_7d_avg_games"] = g["games"].transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean())
    for col in ["difference_medals", "games", "bb", "rb", "rb_probability_calc", "combined_probability_calc"]:
        out[f"prev_{col}"] = g[col].shift(1)
    out["prev_high_behavior_flag"] = ((out["prev_games"] >= 7000) & (out["prev_rb_probability_calc"] <= 300)) | (out["prev_difference_medals"] >= 1000)

    def neg_streak(s: pd.Series) -> pd.Series:
        vals: list[int] = []
        streak = 0
        for v in s.shift(1):
            if pd.notna(v) and v < 0:
                streak += 1
            else:
                streak = 0
            vals.append(streak)
        return pd.Series(vals, index=s.index)

    out["consecutive_negative_days"] = g["difference_medals"].transform(neg_streak)

    def days_since_strong(frame: pd.DataFrame) -> pd.Series:
        strong = (frame["games"] >= 7000) & (frame["rb_probability_calc"] <= 300) | (frame["difference_medals"] >= 1000)
        last_seen = None
        values: list[int | None] = []
        for d, is_strong in zip(frame["date"], strong):
            values.append(None if last_seen is None else (pd.Timestamp(d) - pd.Timestamp(last_seen)).days)
            if bool(is_strong):
                last_seen = d
        return pd.Series(values, index=frame.index)

    out["days_since_strong_behavior"] = pd.NA
    for _, frame in out.groupby(group_cols):
        out.loc[frame.index, "days_since_strong_behavior"] = days_since_strong(frame)
    out = _add_group_trend_features(out)
    return out.sort_values(["date", "machine_number"]).reset_index(drop=True)


def _add_group_trend_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "weekday" not in out.columns:
        out["weekday"] = pd.to_datetime(out["date"]).dt.weekday
    specs = [
        (["store", "machine_name", "machine_last_digit"], "past_60d_last_digit_avg_diff"),
        (["store", "machine_name", "weekday"], "past_60d_weekday_avg_diff"),
    ]
    special_cols = ["is_day_5", "is_day_7", "is_day_11", "is_day_22", "is_month_day_zorome"]
    if set(special_cols).issubset(out.columns):
        out["special_day_key"] = out[special_cols].astype(int).astype(str).agg("-".join, axis=1)
        specs.append((["store", "machine_name", "special_day_key"], "past_60d_special_pattern_avg_diff"))
    for keys, feature_name in specs:
        daily = out.groupby([*keys, "date"], as_index=False)["difference_medals"].mean()
        daily = daily.sort_values([*keys, "date"])
        daily[feature_name] = daily.groupby(keys)["difference_medals"].transform(lambda s: s.shift(1).rolling(60, min_periods=3).mean())
        out = out.merge(daily[[*keys, "date", feature_name]], on=[*keys, "date"], how="left")
    return out


def features_for_prediction(history: pd.DataFrame, target_date: date, special_config: dict) -> pd.DataFrame:
    if history.empty:
        return history
    latest = history.sort_values("date").groupby(["store", "machine_name", "machine_number"], as_index=False).tail(1).copy()
    latest["date"] = target_date
    return add_calendar_features(add_historical_features(pd.concat([history, latest], ignore_index=True)), special_config).query("date == @target_date")
