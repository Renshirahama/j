from __future__ import annotations

import pandas as pd


def evaluate_hypotheses(features: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    def add(name: str, mask: pd.Series) -> None:
        subset = features[mask.fillna(False)]
        baseline = features["difference_medals"].mean() if not features.empty else 0.0
        rows.append(
            {
                "hypothesis": name,
                "sample_size": int(len(subset)),
                "avg_diff": float(subset["difference_medals"].mean()) if len(subset) else 0.0,
                "win_rate": float((subset["difference_medals"] > 0).mean()) if len(subset) else 0.0,
                "avg_reg_probability": float(subset["rb_probability_calc"].mean()) if len(subset) else 0.0,
                "random_diff_delta": float(subset["difference_medals"].mean() - baseline) if len(subset) else 0.0,
                "judgement": "sample_too_small" if len(subset) < 20 else "check_numbers_only",
            }
        )

    add("前日凹み台が翌日強いのか", features["prev_difference_medals"] <= -1000)
    add("前日強かった台が翌日も強いのか", features["prev_difference_medals"] >= 1000)
    add("台番号に強弱があるか", features["past_30d_avg_diff"] > features["past_30d_avg_diff"].median())
    add("台番号末尾に傾向があるか", features.groupby("machine_last_digit")["difference_medals"].transform("mean") > features["difference_medals"].mean())
    add("特定日に強い位置が変化するか", features["is_day_7"] | features["is_day_5"] | features["is_day_11"] | features["is_day_22"])
    add("曜日による違いがあるか", features.groupby("weekday")["difference_medals"].transform("mean") > features["difference_medals"].mean())
    add("直近3-7日の弱い台を上げる傾向があるか", features["past_7d_avg_diff"] < 0)
    add("隣接した複数台が同時に強くなる傾向があるか", features["difference_medals"].gt(1000) & features["machine_number"].shift(1).notna())
    return pd.DataFrame(rows)
