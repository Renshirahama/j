from __future__ import annotations

import pandas as pd


SCORE_PROFILES = {
    "balanced": {
        "reg": 24.0,
        "recent_weak": 15.0,
        "machine_history": 16.0,
        "prev_state": 14.0,
        "games": 8.0,
        "last_digit": 9.0,
        "weekday": 7.0,
        "calendar": 7.0,
    },
    "reg_quality": {
        "reg": 42.0,
        "recent_weak": 6.0,
        "machine_history": 15.0,
        "prev_state": 6.0,
        "games": 16.0,
        "last_digit": 5.0,
        "weekday": 5.0,
        "calendar": 5.0,
    },
    "raise_after_weak": {
        "reg": 16.0,
        "recent_weak": 31.0,
        "machine_history": 6.0,
        "prev_state": 24.0,
        "games": 6.0,
        "last_digit": 7.0,
        "weekday": 5.0,
        "calendar": 5.0,
    },
    "carryover": {
        "reg": 22.0,
        "recent_weak": 0.0,
        "machine_history": 28.0,
        "prev_strong": 22.0,
        "games": 10.0,
        "last_digit": 8.0,
        "weekday": 5.0,
        "calendar": 5.0,
    },
    "number_calendar": {
        "reg": 12.0,
        "recent_weak": 8.0,
        "machine_history": 14.0,
        "prev_state": 8.0,
        "games": 6.0,
        "last_digit": 24.0,
        "weekday": 16.0,
        "calendar": 12.0,
    },
}


def _scale(series: pd.Series, invert: bool = False) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if invert:
        s = -s
    if s.notna().sum() == 0 or s.max() == s.min():
        return pd.Series(0.5, index=series.index)
    return ((s - s.min()) / (s.max() - s.min())).fillna(0.5)


def score_candidates(features: pd.DataFrame, profile: str = "balanced") -> pd.DataFrame:
    out = features.copy()
    weights = SCORE_PROFILES[profile]
    reg_score = _scale(out.get("past_7d_reg_probability"), invert=True)
    weak_score = _scale(out.get("past_7d_avg_diff"), invert=True)
    hist_score = _scale(out.get("past_30d_avg_diff"))
    prev_state = _scale(out.get("consecutive_negative_days")) * 0.55 + _scale(out.get("prev_difference_medals"), invert=True) * 0.45
    prev_strong = _scale(out.get("prev_difference_medals")) * 0.5 + _scale(out.get("prev_games")) * 0.2 + _scale(out.get("prev_rb_probability_calc"), invert=True) * 0.3
    games_score = _scale(out.get("past_7d_avg_games"))
    last_digit_score = _scale(out.get("past_60d_last_digit_avg_diff"))
    weekday_score = _scale(out.get("past_60d_weekday_avg_diff"))
    calendar_score = (
        out.get("is_weekend", False).astype(float) * 0.15
        + out.get("is_day_5", False).astype(float) * 0.2
        + out.get("is_day_7", False).astype(float) * 0.25
        + out.get("is_day_11", False).astype(float) * 0.15
        + out.get("is_day_22", False).astype(float) * 0.15
        + out.get("is_month_day_zorome", False).astype(float) * 0.1
    )
    out["score"] = (
        reg_score * weights.get("reg", 0.0)
        + weak_score * weights.get("recent_weak", 0.0)
        + hist_score * weights.get("machine_history", 0.0)
        + prev_state * weights.get("prev_state", 0.0)
        + prev_strong * weights.get("prev_strong", 0.0)
        + games_score * weights.get("games", 0.0)
        + last_digit_score * weights.get("last_digit", 0.0)
        + weekday_score * weights.get("weekday", 0.0)
        + calendar_score * weights.get("calendar", 0.0)
    ).round(2)
    out["score_profile"] = profile
    out["reason_reg"] = reg_score
    out["reason_recent_weak"] = weak_score
    out["reason_machine_history"] = hist_score
    out["reason_prev_state"] = prev_state
    out["reason_prev_strong"] = prev_strong
    out["reason_games"] = games_score
    out["reason_last_digit"] = last_digit_score
    out["reason_weekday"] = weekday_score
    return out.sort_values(["score", "machine_number"], ascending=[False, True]).reset_index(drop=True)


def explain_row(row: pd.Series) -> list[str]:
    reasons = []
    if row.get("reason_reg", 0) >= 0.6:
        reasons.append("過去7日REG確率が相対的に良好")
    if row.get("reason_recent_weak", 0) >= 0.6:
        reasons.append("直近7日差枚が弱めで上げ候補として評価")
    if row.get("reason_machine_history", 0) >= 0.6:
        reasons.append("過去30日差枚の台別傾向が相対的に良い")
    if row.get("reason_prev_state", 0) >= 0.6:
        reasons.append("前日状態が凹み・連続マイナス寄り")
    if row.get("score_profile") == "carryover" and row.get("reason_prev_strong", 0) >= 0.6:
        reasons.append("前日強めの挙動を据え置き寄りに評価")
    if row.get("reason_games", 0) >= 0.6:
        reasons.append("過去7日平均G数が高くサンプル信頼度が比較的高い")
    if row.get("reason_last_digit", 0) >= 0.6:
        reasons.append("同機種内の台番号末尾傾向が相対的に良い")
    if row.get("reason_weekday", 0) >= 0.6:
        reasons.append("同機種内の曜日傾向が相対的に良い")
    if row.get("is_day_7", False) or row.get("is_day_5", False) or row.get("is_day_11", False) or row.get("is_day_22", False):
        reasons.append("設定ファイル上の特定日条件に該当")
    return reasons[:5] or ["利用可能な過去データ内で総合スコアが相対的に上位"]
