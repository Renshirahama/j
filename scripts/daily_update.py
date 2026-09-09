from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from collectors.slonavi_importer import RobotsUnavailableError, fetch_html, parse_slonavi_html  # noqa: E402
from juggler_analysis.cleaning import normalize_probabilities  # noqa: E402
from juggler_analysis.config import config_path, load_yaml  # noqa: E402
from juggler_analysis.database import connect, upsert_results  # noqa: E402
from juggler_analysis.export import build_dashboard_payload, write_dashboard_payload  # noqa: E402


def update_job(job: dict, target_date: date, source_cfg: dict, special_cfg: dict, label_cfg: dict) -> None:
    from collectors.slonavi_importer import SloNaviConfig

    url = f"{source_cfg['base_url'].rstrip('/')}/data/{target_date.isoformat()}-{job['hall_id']}/"
    cfg = SloNaviConfig(
        base_url=source_cfg["base_url"],
        hall_id=str(job["hall_id"]),
        request_delay_seconds=float(source_cfg["request_delay_seconds"]),
        user_agent=source_cfg["user_agent"],
    )
    html = fetch_html(url, cfg)
    raw_path = ROOT / "data/raw/slonavi" / f"{job['id']}-{target_date.isoformat()}.html"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(html, encoding="utf-8")
    df = parse_slonavi_html(html, target_date, str(job["store"]), str(job["machine"]))
    df = normalize_probabilities(df)
    db_path = ROOT / str(job["db"])
    conn = connect(db_path)
    changed = upsert_results(conn, df)
    conn.close()
    conn = connect(db_path)
    from juggler_analysis.database import load_results

    all_df = load_results(conn, str(job["store"]), None)
    conn.close()
    payload = build_dashboard_payload(
        all_df,
        special_cfg,
        label_cfg,
        label_cfg["default_label"],
        display_machine_name="ジャグラー",
        score_profile=str(job["score_profile"]),
    )
    out_path = ROOT / str(job["out"])
    write_dashboard_payload(payload, out_path)
    logging.info("%s: updated %s rows; dashboard=%s target_date=%s", job["id"], changed, out_path, payload["target_date"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Import yesterday's Slo-Navi data and refresh the dashboard.")
    parser.add_argument("--date", type=date.fromisoformat, help="Date to import (default: yesterday).")
    parser.add_argument("--job", help="Only update one configured job (default: all jobs).")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(ROOT / "data/processed/daily_update.log", encoding="utf-8"), logging.StreamHandler()],
    )
    target_date = args.date or (date.today() - timedelta(days=1))
    source_cfg = load_yaml(config_path("sources.yaml"))["sources"]["slo_navi"]
    jobs = load_yaml(config_path("daily_update.yaml"))["jobs"]
    if args.job:
        jobs = [job for job in jobs if job["id"] == args.job]
        if not jobs:
            raise SystemExit(f"unknown job: {args.job}")
    special_cfg = load_yaml(config_path("special_days.yaml"))
    label_cfg = load_yaml(config_path("labels.yaml"))
    failed = 0
    for job in jobs:
        try:
            update_job(job, target_date, source_cfg, special_cfg, label_cfg)
        except Exception as exc:
            failed += 1
            logging.exception("%s: daily import failed for %s: %s", job["id"], target_date, exc)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
