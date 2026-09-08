from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from juggler_analysis.backtest import walk_forward_backtest
from juggler_analysis.cleaning import normalize_probabilities
from juggler_analysis.features import add_calendar_features, add_historical_features
from juggler_analysis.scoring import score_candidates
from collectors.slonavi_importer import parse_slonavi_html


SPECIAL = {"special_days": {"day_5": {"days": [5, 15, 25]}, "day_7": {"contains_digit": 7}, "day_11": {"days": [11]}, "day_22": {"days": [22]}, "month_day_zorome": {"same_month_day_digit": True}}}
LABELS = {"labels": {"same_machine_top20": {"type": "same_day_quantile", "quantile": 0.8}}, "default_label": "same_machine_top20"}


def sample_df(days: int = 35) -> pd.DataFrame:
    rows = []
    start = date(2026, 1, 1)
    for i in range(days):
        for machine in ["2181", "2182", "2183"]:
            rows.append(
                {
                    "date": start + timedelta(days=i),
                    "store": "エスパス日拓渋谷駅前新館",
                    "machine_name": "マイジャグラーV",
                    "machine_number": machine,
                    "games": 7000 + i,
                    "bb": 25,
                    "rb": 20 + (machine == "2183"),
                    "difference_medals": (i * 10) + (200 if machine == "2183" else -100),
                }
            )
    return pd.DataFrame(rows)


def test_probability_calculation() -> None:
    df = normalize_probabilities(sample_df(1))
    row = df.iloc[0]
    assert row["bb_probability"] == row["games"] / row["bb"]
    assert row["combined_probability"] == row["games"] / (row["bb"] + row["rb"])


def test_rolling_features_use_past_only() -> None:
    df = add_historical_features(sample_df(10))
    machine = df[df["machine_number"] == "2181"].sort_values("date")
    expected = sample_df(10)
    expected = expected[expected["machine_number"] == "2181"]["difference_medals"].iloc[:3].mean()
    assert machine.iloc[3]["past_3d_avg_diff"] == expected


def test_previous_day_features() -> None:
    df = add_historical_features(sample_df(3))
    machine = df[df["machine_number"] == "2182"].sort_values("date")
    assert machine.iloc[1]["prev_difference_medals"] == machine.iloc[0]["difference_medals"]
    assert machine.iloc[1]["prev_games"] == machine.iloc[0]["games"]


def test_future_leakage_prevention() -> None:
    base = sample_df(8)
    changed_future = base.copy()
    mask = (changed_future["date"] == date(2026, 1, 8)) & (changed_future["machine_number"] == "2181")
    changed_future.loc[mask, "difference_medals"] = 99999
    f1 = add_historical_features(base)
    f2 = add_historical_features(changed_future)
    target = (f1["date"] == date(2026, 1, 7)) & (f1["machine_number"] == "2181")
    cols = ["past_7d_avg_diff", "prev_difference_medals", "consecutive_negative_days"]
    assert f1.loc[target, cols].reset_index(drop=True).equals(f2.loc[target, cols].reset_index(drop=True))


def test_ranking() -> None:
    features = add_calendar_features(add_historical_features(sample_df(35)), SPECIAL)
    ranked = score_candidates(features[features["date"] == max(features["date"])])
    assert list(ranked["score"]) == sorted(ranked["score"], reverse=True)
    assert ranked.iloc[0]["machine_number"] in {"2181", "2182", "2183"}


def test_backtest() -> None:
    result = walk_forward_backtest(sample_df(40), SPECIAL, LABELS, "same_machine_top20", min_train_days=30, random_trials=20)
    assert result.metrics["evaluated_days"] == 10
    assert "top3_avg_diff" in result.metrics
    assert result.random_metrics["random_trials"] > 0


def test_slonavi_section_parser() -> None:
    html = """
    <html><body>
    <h1>2026年08月26日(水)</h1>
    <div>エスパス日拓渋谷駅前新館</div>
    <h2>マイジャグラーV</h2>
    <table>
      <tr><th>台番号</th><th>G数</th><th>差枚</th><th>BB</th><th>RB</th><th>合成確率</th></tr>
      <tr><td>2177</td><td>6,835</td><td>+2,000</td><td>33</td><td>24</td><td>1/119.9</td></tr>
    </table>
    </body></html>
    """
    df = parse_slonavi_html(html, None, "エスパス日拓渋谷駅前新館", "マイジャグラーV")
    assert df.iloc[0]["date"] == date(2026, 8, 26)
    assert df.iloc[0]["machine_number"] == "2177"
    assert df.iloc[0]["games"] == 6835
    assert df.iloc[0]["difference_medals"] == 2000


def test_slonavi_juggler_wide_parser_keeps_actual_machine_name() -> None:
    html = """
    <html><body>
    <h1>2026年08月30日(日)</h1>
    <div>エスパス日拓溝の口駅前新館</div>
    <table>
      <tr><th>機種名</th><th>台番号</th><th>G数</th><th>差枚</th><th>BB</th><th>RB</th></tr>
      <tr><td>ファンキージャグラー2</td><td>2085</td><td>3,552</td><td>-500</td><td>13</td><td>5</td></tr>
      <tr><td>北斗の拳</td><td>2142</td><td>486</td><td>-400</td><td>1</td><td>1</td></tr>
      <tr><td>マイジャグラーV</td><td>2066</td><td>6,659</td><td>0</td><td>26</td><td>18</td></tr>
    </table>
    </body></html>
    """
    df = parse_slonavi_html(html, None, "エスパス日拓溝の口駅前新館", "ジャグラー")
    assert set(df["machine_name"]) == {"ファンキージャグラー2", "マイジャグラーV"}
    assert len(df) == 2
