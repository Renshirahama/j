from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pandas as pd

from .backtest import compare_score_profiles, walk_forward_backtest
from .features import add_calendar_features, add_historical_features, features_for_prediction
from .hypotheses import evaluate_hypotheses
from .scoring import explain_row, score_candidates


def build_dashboard_payload(df: pd.DataFrame, special_config: dict, label_config: dict, label_name: str, display_machine_name: str | None = None) -> dict:
    latest_date = max(df["date"])
    target_date = pd.Timestamp(latest_date).date() + timedelta(days=1)
    pred_features = features_for_prediction(df, target_date, special_config)
    scorer_comparison = compare_score_profiles(df, special_config, label_config, label_name)
    best_profile = str(scorer_comparison.iloc[0]["score_profile"]) if not scorer_comparison.empty else "balanced"
    ranking = score_candidates(pred_features, profile=best_profile)
    ranking["reasons"] = ranking.apply(explain_row, axis=1)
    backtest = walk_forward_backtest(df, special_config, label_config, label_name, score_profile=best_profile)
    prepared = add_calendar_features(add_historical_features(df), special_config)
    hypotheses = evaluate_hypotheses(prepared)
    machine_comparison = compare_machines(df, special_config, label_config, label_name)
    charts = build_charts(prepared, backtest.picks)
    return {
        "store": str(df["store"].iloc[0]),
        "machine_name": display_machine_name or str(df["machine_name"].iloc[0]),
        "latest_date": str(latest_date),
        "target_date": str(target_date),
        "ranking": json.loads(
            ranking[
                [
                    "machine_name",
                    "machine_number",
                    "score",
                    "reasons",
                    "past_7d_avg_diff",
                    "past_7d_reg_probability",
                    "prev_difference_medals",
                ]
            ]
            .head(20)
            .to_json(orient="records", force_ascii=False)
        ),
        "backtest": backtest.metrics,
        "random": backtest.random_metrics,
        "scorer_comparison": json.loads(scorer_comparison.to_json(orient="records", force_ascii=False)),
        "machine_comparison": machine_comparison,
        "hypotheses": json.loads(hypotheses.to_json(orient="records", force_ascii=False)),
        "charts": charts,
    }


def compare_machines(df: pd.DataFrame, special_config: dict, label_config: dict, label_name: str) -> list[dict]:
    rows = []
    for machine_name, part in df.groupby("machine_name"):
        if part["date"].nunique() < 45 or part["machine_number"].nunique() < 3:
            continue
        profile_table = compare_score_profiles(part, special_config, label_config, label_name, random_trials=200)
        if profile_table.empty:
            continue
        best = profile_table.iloc[0].to_dict()
        rows.append(
            {
                "machine_name": str(machine_name),
                "days": int(part["date"].nunique()),
                "machines": int(part["machine_number"].nunique()),
                "best_profile": str(best.get("score_profile")),
                "top3_avg_diff": float(best.get("top3_avg_diff", 0.0)),
                "random_avg": float(best.get("random_random_avg", 0.0)),
                "top3_vs_random_delta": float(best.get("top3_vs_random_delta", 0.0)),
                "top3_plus_rate": float(best.get("top3_plus_rate", 0.0)),
                "predictive_power": str(best.get("predictive_power", "not_confirmed")),
            }
        )
    return sorted(rows, key=lambda x: (x["top3_vs_random_delta"], x["top3_avg_diff"]), reverse=True)


def build_charts(df: pd.DataFrame, picks: pd.DataFrame) -> dict:
    by_machine = df.groupby("machine_number", as_index=False)["difference_medals"].mean().rename(columns={"difference_medals": "avg_diff"})
    by_weekday = df.groupby("weekday", as_index=False)["difference_medals"].mean().rename(columns={"difference_medals": "avg_diff"})
    special = pd.DataFrame(
        [
            {"name": "5の日", "avg_diff": df[df["is_day_5"]]["difference_medals"].mean()},
            {"name": "7のつく日", "avg_diff": df[df["is_day_7"]]["difference_medals"].mean()},
            {"name": "11日", "avg_diff": df[df["is_day_11"]]["difference_medals"].mean()},
            {"name": "22日", "avg_diff": df[df["is_day_22"]]["difference_medals"].mean()},
            {"name": "月日ゾロ目", "avg_diff": df[df["is_month_day_zorome"]]["difference_medals"].mean()},
        ]
    ).fillna(0)
    scatter_prev = df[["prev_difference_medals", "difference_medals"]].dropna().rename(columns={"prev_difference_medals": "x", "difference_medals": "y"}).head(500)
    score_scatter = picks[picks["k"] == 3][["score", "difference_medals"]].rename(columns={"score": "x", "difference_medals": "y"}).head(500) if not picks.empty else pd.DataFrame(columns=["x", "y"])
    top3_daily = picks[picks["k"] == 3].groupby("date", as_index=False)["difference_medals"].mean() if not picks.empty else pd.DataFrame(columns=["date", "difference_medals"])
    if not top3_daily.empty:
        top3_daily["cumulative"] = top3_daily["difference_medals"].cumsum()
        top3_daily["date"] = top3_daily["date"].astype(str)
    heat = df[["date", "machine_number", "difference_medals"]].copy()
    heat["date"] = heat["date"].astype(str)
    return {
        "by_machine_avg_diff": json.loads(by_machine.to_json(orient="records", force_ascii=False)),
        "heatmap": json.loads(heat.tail(1500).to_json(orient="records", force_ascii=False)),
        "by_weekday_avg_diff": json.loads(by_weekday.to_json(orient="records", force_ascii=False)),
        "by_special_day_avg_diff": json.loads(special.to_json(orient="records", force_ascii=False)),
        "prev_vs_next_diff": json.loads(scatter_prev.to_json(orient="records", force_ascii=False)),
        "score_vs_actual_diff": json.loads(score_scatter.to_json(orient="records", force_ascii=False)),
        "top3_cumulative_diff": json.loads(top3_daily.to_json(orient="records", force_ascii=False)),
    }


def write_dashboard_payload(payload: dict, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
