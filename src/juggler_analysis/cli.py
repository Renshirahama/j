from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from collectors.csv_importer import read_csv
from collectors.slonavi_importer import SloNaviConfig, fetch_html, fetch_range, parse_slonavi_html
from collectors.slonavi_importer import RobotsUnavailableError
from juggler_analysis.cleaning import normalize_probabilities, quality_report
from juggler_analysis.config import ROOT, config_path, load_yaml
from juggler_analysis.database import connect, load_results, upsert_results
from juggler_analysis.export import build_dashboard_payload, write_dashboard_payload
from juggler_analysis.features import add_calendar_features, add_historical_features
from juggler_analysis.scoring import score_candidates


DEFAULT_DB = ROOT / "data" / "db" / "juggler.sqlite"


def cmd_init_db(args: argparse.Namespace) -> None:
    connect(args.db).close()
    print(f"initialized: {args.db}")


def cmd_import_csv(args: argparse.Namespace) -> None:
    store_cfg = load_yaml(config_path("store.yaml"))
    df = read_csv(args.csv, store=args.store or store_cfg["store"])
    report = quality_report(df)
    if not report.empty:
        out = ROOT / "data" / "processed" / "quality_report.csv"
        report.to_csv(out, index=False)
        print(f"quality issues found: {len(report)} rows, report={out}")
    df = normalize_probabilities(df)
    conn = connect(args.db)
    changed = upsert_results(conn, df)
    conn.close()
    print(f"imported_or_updated_rows: {changed}")


def _slonavi_config() -> SloNaviConfig:
    cfg = load_yaml(config_path("sources.yaml"))["sources"]["slo_navi"]
    return SloNaviConfig(
        base_url=cfg["base_url"],
        hall_id=str(cfg["hall_id"]),
        request_delay_seconds=float(cfg["request_delay_seconds"]),
        user_agent=cfg["user_agent"],
    )


def _store_name(args: argparse.Namespace) -> str:
    return args.store or load_yaml(config_path("store.yaml"))["store"]


def _machine_name(args: argparse.Namespace) -> str:
    return args.machine or load_yaml(config_path("store.yaml"))["machine_name"]


def _source_config(args: argparse.Namespace) -> SloNaviConfig:
    cfg = _slonavi_config()
    if getattr(args, "hall_id", None):
        return SloNaviConfig(
            base_url=cfg.base_url,
            hall_id=str(args.hall_id),
            request_delay_seconds=cfg.request_delay_seconds,
            user_agent=cfg.user_agent,
        )
    return cfg


def _save_imported(df: pd.DataFrame, db: str) -> None:
    report = quality_report(df)
    if not report.empty:
        out = ROOT / "data" / "processed" / "quality_report.csv"
        report.to_csv(out, index=False)
        print(f"quality issues found: {len(report)} rows, report={out}")
    df = normalize_probabilities(df)
    conn = connect(db)
    changed = upsert_results(conn, df)
    conn.close()
    print(f"imported_or_updated_rows: {changed}")


def cmd_import_slonavi_url(args: argparse.Namespace) -> None:
    cfg = _source_config(args)
    try:
        html = fetch_html(args.url, cfg)
    except RobotsUnavailableError as exc:
        raise SystemExit(f"cannot verify robots.txt, stopped without fetching data page: {exc}") from exc
    except PermissionError as exc:
        raise SystemExit(str(exc)) from exc
    raw_out = ROOT / "data" / "raw" / "slonavi" / f"{args.date or 'unknown'}.html"
    raw_out.parent.mkdir(parents=True, exist_ok=True)
    raw_out.write_text(html, encoding="utf-8")
    target_date = pd.to_datetime(args.date).date() if args.date else None
    df = parse_slonavi_html(html, target_date, _store_name(args), _machine_name(args))
    _save_imported(df, args.db)


def cmd_import_slonavi_range(args: argparse.Namespace) -> None:
    cfg = _source_config(args)
    start = pd.to_datetime(args.start).date()
    end = pd.to_datetime(args.end).date()
    try:
        df, errors = fetch_range(start, end, cfg, _store_name(args), _machine_name(args), continue_on_error=args.continue_on_error)
    except RobotsUnavailableError as exc:
        raise SystemExit(f"cannot verify robots.txt, stopped without fetching data page: {exc}") from exc
    except PermissionError as exc:
        raise SystemExit(str(exc)) from exc
    if not errors.empty:
        out = ROOT / "data" / "processed" / "slonavi_fetch_errors.csv"
        errors.to_csv(out, index=False)
        print(f"fetch errors: {len(errors)} days, report={out}")
    if df.empty:
        raise SystemExit("no rows fetched")
    _save_imported(df, args.db)


def cmd_parse_slonavi_html(args: argparse.Namespace) -> None:
    html = Path(args.html).read_text(encoding="utf-8")
    target_date = pd.to_datetime(args.date).date() if args.date else None
    df = parse_slonavi_html(html, target_date, _store_name(args), _machine_name(args))
    _save_imported(df, args.db)


def cmd_generate_sample(args: argparse.Namespace) -> None:
    rng = np.random.default_rng(7)
    rows = []
    start = date.today() - timedelta(days=args.days)
    machines = [str(n) for n in range(2180, 2180 + args.machines)]
    for d in [start + timedelta(days=i) for i in range(args.days)]:
        day_boost = 250 if d.day in [5, 7, 11, 17, 22, 27] else 0
        for m in machines:
            bias = (int(m[-1]) - 4) * 35
            games = int(np.clip(rng.normal(6200, 1200), 2500, 9000))
            rb_rate = int(np.clip(rng.normal(310 - bias / 20, 30), 230, 430))
            bb_rate = int(np.clip(rng.normal(270, 35), 220, 420))
            rb = max(0, round(games / rb_rate))
            bb = max(0, round(games / bb_rate))
            diff = int(rng.normal(bias + day_boost, 900))
            rows.append(
                {
                    "date": d.isoformat(),
                    "machine_name": "マイジャグラーV",
                    "machine_number": m,
                    "games": games,
                    "bb": bb,
                    "rb": rb,
                    "difference_medals": diff,
                }
            )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"sample_csv: {out}")


def cmd_rank(args: argparse.Namespace) -> None:
    special_cfg = load_yaml(config_path("special_days.yaml"))
    conn = connect(args.db)
    df = load_results(conn, _store_name(args), None)
    conn.close()
    machine = _machine_name(args)
    df = df[df["machine_name"].astype(str).str.contains(machine, na=False)] if machine == "ジャグラー" else df[df["machine_name"] == machine]
    if df.empty:
        raise SystemExit("no data. import CSV first.")
    features = add_calendar_features(add_historical_features(df), special_cfg)
    ranked = score_candidates(features[features["date"] == max(features["date"])])
    print(ranked[["machine_number", "score", "past_7d_avg_diff", "past_7d_reg_probability", "prev_difference_medals"]].head(args.top).to_string(index=False))


def cmd_export_dashboard(args: argparse.Namespace) -> None:
    special_cfg = load_yaml(config_path("special_days.yaml"))
    label_cfg = load_yaml(config_path("labels.yaml"))
    conn = connect(args.db)
    df = load_results(conn, _store_name(args), None)
    conn.close()
    machine = _machine_name(args)
    df = df[df["machine_name"].astype(str).str.contains(machine, na=False)] if machine == "ジャグラー" else df[df["machine_name"] == machine]
    if df["date"].nunique() < args.min_days:
        raise SystemExit(f"need at least {args.min_days} business days, found {df['date'].nunique()}")
    payload = build_dashboard_payload(df, special_cfg, label_cfg, label_cfg["default_label"], display_machine_name=machine)
    write_dashboard_payload(payload, args.out)
    print(f"dashboard_json: {args.out}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(DEFAULT_DB))
    sub = parser.add_subparsers(required=True)
    p = sub.add_parser("init-db")
    p.set_defaults(func=cmd_init_db)
    p = sub.add_parser("import-csv")
    p.add_argument("csv")
    p.add_argument("--store")
    p.set_defaults(func=cmd_import_csv)
    p = sub.add_parser("import-slonavi-url")
    p.add_argument("url")
    p.add_argument("--date")
    p.add_argument("--store")
    p.add_argument("--machine")
    p.add_argument("--hall-id")
    p.set_defaults(func=cmd_import_slonavi_url)
    p = sub.add_parser("import-slonavi-range")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--continue-on-error", action="store_true")
    p.add_argument("--store")
    p.add_argument("--machine")
    p.add_argument("--hall-id")
    p.set_defaults(func=cmd_import_slonavi_range)
    p = sub.add_parser("parse-slonavi-html")
    p.add_argument("html")
    p.add_argument("--date")
    p.add_argument("--store")
    p.add_argument("--machine")
    p.add_argument("--hall-id")
    p.set_defaults(func=cmd_parse_slonavi_html)
    p = sub.add_parser("generate-sample")
    p.add_argument("--out", default=str(ROOT / "data" / "raw" / "sample_my_juggler_v.csv"))
    p.add_argument("--days", type=int, default=70)
    p.add_argument("--machines", type=int, default=10)
    p.set_defaults(func=cmd_generate_sample)
    p = sub.add_parser("rank")
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--store")
    p.add_argument("--machine")
    p.set_defaults(func=cmd_rank)
    p = sub.add_parser("export-dashboard")
    p.add_argument("--out", default=str(ROOT / "web" / "public" / "dashboard.json"))
    p.add_argument("--min-days", type=int, default=30)
    p.add_argument("--store")
    p.add_argument("--machine")
    p.set_defaults(func=cmd_export_dashboard)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
