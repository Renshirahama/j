from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .features import add_calendar_features, add_historical_features
from .labels import apply_label
from .scoring import SCORE_PROFILES, score_candidates


@dataclass(frozen=True)
class BacktestResult:
    picks: pd.DataFrame
    metrics: dict[str, float | int | str]
    random_metrics: dict[str, float | int]


def walk_forward_backtest(
    df: pd.DataFrame,
    special_config: dict,
    label_config: dict,
    label_name: str,
    min_train_days: int = 30,
    random_trials: int = 1000,
    seed: int = 42,
    score_profile: str = "balanced",
) -> BacktestResult:
    prepared = add_calendar_features(add_historical_features(df), special_config)
    prepared["proxy_label"] = apply_label(prepared, label_config, label_name)
    dates = sorted(prepared["date"].unique())
    pick_rows: list[dict[str, object]] = []
    rng = np.random.default_rng(seed)
    random_top3_means: list[float] = []
    random_daily_rows: list[dict[str, float]] = []

    for i in range(min_train_days, len(dates)):
        target_date = dates[i]
        day = prepared[prepared["date"] == target_date].copy()
        if day.empty:
            continue
        ranked = score_candidates(day, profile=score_profile)
        for k in [1, 3, 5]:
            for rank, (_, row) in enumerate(ranked.head(k).iterrows(), start=1):
                pick_rows.append(
                    {
                        "date": target_date,
                        "k": k,
                        "rank": rank,
                        "machine_number": row["machine_number"],
                        "machine_name": row["machine_name"],
                        "score": row["score"],
                        "score_profile": score_profile,
                        "difference_medals": row["difference_medals"],
                        "games": row["games"],
                        "rb_probability": row["rb_probability_calc"],
                        "proxy_label": bool(row["proxy_label"]),
                    }
                )
        day_values = day["difference_medals"].to_numpy()
        if len(day_values) >= 3:
            trial_means = [float(np.mean(rng.choice(day_values, size=3, replace=False))) for _ in range(random_trials)]
            random_top3_means.extend(trial_means)
            random_daily_rows.append({"date": target_date, "random_top3_mean": float(np.mean(trial_means))})

    picks = pd.DataFrame(pick_rows)
    metrics = summarize_picks(picks, prepared, label_name)
    random_metrics = summarize_random(random_top3_means)
    if random_daily_rows:
        metrics["random_top3_daily_mean"] = float(pd.DataFrame(random_daily_rows)["random_top3_mean"].mean())
    pred_top3 = metrics.get("top3_avg_diff", 0.0)
    rand_avg = random_metrics.get("random_avg", 0.0)
    rand_hi = random_metrics.get("random_95_hi", 0.0)
    metrics["predictive_power"] = "confirmed_vs_random_95" if pred_top3 > rand_hi else "not_confirmed"
    metrics["label_name"] = label_name
    metrics["score_profile"] = score_profile
    return BacktestResult(picks=picks, metrics=metrics, random_metrics=random_metrics)


def compare_score_profiles(
    df: pd.DataFrame,
    special_config: dict,
    label_config: dict,
    label_name: str,
    min_train_days: int = 30,
    random_trials: int = 300,
) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for profile in SCORE_PROFILES:
        result = walk_forward_backtest(
            df,
            special_config,
            label_config,
            label_name,
            min_train_days=min_train_days,
            random_trials=random_trials,
            score_profile=profile,
        )
        row = {"score_profile": profile, **result.metrics, **{f"random_{k}": v for k, v in result.random_metrics.items()}}
        row["top3_vs_random_delta"] = float(row.get("top3_avg_diff", 0.0)) - float(row.get("random_random_avg", 0.0))
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["top3_vs_random_delta", "top3_avg_diff"], ascending=[False, False]).reset_index(drop=True)


def summarize_picks(picks: pd.DataFrame, prepared: pd.DataFrame, label_name: str) -> dict[str, float | int | str]:
    out: dict[str, float | int | str] = {"evaluated_days": int(picks["date"].nunique()) if not picks.empty else 0}
    if picks.empty:
        return out
    for k in [1, 3, 5]:
        subset = picks[picks["k"] == k]
        out[f"top{k}_avg_diff"] = float(subset["difference_medals"].mean())
        out[f"top{k}_plus_rate"] = float((subset["difference_medals"] > 0).mean())
        if k in [3, 5]:
            dates = subset["date"].unique()
            caught = []
            for d in dates:
                day_labels = set(
                    prepared[(prepared["date"] == d) & (prepared["proxy_label"])][["machine_name", "machine_number"]].itertuples(index=False, name=None)
                )
                selected = set(subset[subset["date"] == d][["machine_name", "machine_number"]].itertuples(index=False, name=None))
                caught.append(0.0 if not day_labels else len(day_labels & selected) / len(day_labels))
            out[f"top{k}_proxy_capture_rate"] = float(np.mean(caught)) if caught else 0.0
    top3 = picks[picks["k"] == 3]
    out["top3_avg_reg_probability"] = float(top3["rb_probability"].mean())
    out["top3_avg_games"] = float(top3["games"].mean())
    out["past30_wins"] = int(top3.groupby("date")["difference_medals"].mean().tail(30).gt(0).sum())
    out["past30_losses"] = int(top3.groupby("date")["difference_medals"].mean().tail(30).le(0).sum())
    return out


def summarize_random(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"random_trials": 0, "random_avg": 0.0, "random_95_lo": 0.0, "random_95_hi": 0.0}
    arr = np.asarray(values)
    return {
        "random_trials": int(len(values)),
        "random_avg": float(np.mean(arr)),
        "random_95_lo": float(np.quantile(arr, 0.025)),
        "random_95_hi": float(np.quantile(arr, 0.975)),
    }
