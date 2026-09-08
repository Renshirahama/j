from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date, timedelta
from io import StringIO
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup


class RobotsUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class SloNaviConfig:
    base_url: str
    hall_id: str
    request_delay_seconds: float
    user_agent: str


def data_url(target_date: date, cfg: SloNaviConfig) -> str:
    return f"{cfg.base_url.rstrip('/')}/data/{target_date.isoformat()}-{cfg.hall_id}/"


def assert_robots_allowed(url: str, user_agent: str) -> None:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    try:
        res = requests.get(robots_url, headers={"User-Agent": user_agent}, timeout=15)
    except requests.RequestException as exc:
        raise RobotsUnavailableError(f"robots.txt could not be fetched: {robots_url} ({exc})") from exc
    if res.status_code >= 500:
        raise RobotsUnavailableError(f"robots.txt temporarily unavailable: {robots_url} status={res.status_code}")
    if res.status_code == 429:
        raise RobotsUnavailableError(f"robots.txt rate limited: {robots_url}")
    if res.status_code >= 400:
        # RFC 9309 treats many 4xx responses as no robots restrictions. Keep the behavior explicit.
        rp.parse([])
    else:
        rp.parse(res.text.splitlines())
    if not rp.can_fetch(user_agent, url):
        raise PermissionError(f"robots.txt disallows fetching: {url}")


def fetch_html(url: str, cfg: SloNaviConfig) -> str:
    assert_robots_allowed(url, cfg.user_agent)
    res = requests.get(url, headers={"User-Agent": cfg.user_agent}, timeout=20)
    res.raise_for_status()
    return res.text


def parse_slonavi_html(html: str, target_date: date | None, store: str, machine_name: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, "lxml")
    page_text = soup.get_text("\n")
    parsed_date = target_date or _parse_date(page_text)
    parsed_store = store or _parse_store(page_text)
    rows = _parse_wide_tables(html, parsed_date, parsed_store, machine_name)
    if rows.empty:
        rows = _parse_section_table(soup, parsed_date, parsed_store, machine_name)
    if rows.empty:
        raise ValueError(f"machine table not found: {machine_name}")
    return rows


def fetch_range(start: date, end: date, cfg: SloNaviConfig, store: str, machine_name: str, continue_on_error: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    errors: list[dict[str, str]] = []
    current = start
    while current <= end:
        url = data_url(current, cfg)
        try:
            html = fetch_html(url, cfg)
            frames.append(parse_slonavi_html(html, current, store, machine_name))
        except Exception as exc:
            if not continue_on_error:
                raise
            errors.append({"date": current.isoformat(), "url": url, "error": str(exc)})
        time.sleep(cfg.request_delay_seconds)
        current += timedelta(days=1)
    data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return data, pd.DataFrame(errors)


def _parse_date(text: str) -> date:
    m = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", text)
    if not m:
        raise ValueError("date not found in page")
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _parse_store(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if "エスパス" in line:
            return line
    return ""


def _parse_wide_tables(html: str, parsed_date: date, store: str, machine_name: str) -> pd.DataFrame:
    rows = []
    for table in pd.read_html(StringIO(html)):
        table = _flatten_columns(table)
        if {"機種名", "台番号", "G数", "差枚", "BB", "RB"}.issubset(set(table.columns)):
            names = table["機種名"].astype(str).str.strip()
            if machine_name == "ジャグラー":
                part = table[names.str.contains("ジャグラー", na=False)].copy()
            else:
                part = table[names == machine_name].copy()
            if not part.empty:
                rows.append(_normalize_table(part, parsed_date, store, machine_name))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _parse_section_table(soup: BeautifulSoup, parsed_date: date, store: str, machine_name: str) -> pd.DataFrame:
    for node in soup.find_all(string=lambda s: bool(s and machine_name in s)):
        table = node.find_parent().find_next("table") if node.find_parent() else None
        if table:
            frames = pd.read_html(StringIO(str(table)))
            if frames:
                parsed = _flatten_columns(frames[0])
                if {"台番号", "G数", "差枚", "BB", "RB"}.issubset(set(parsed.columns)):
                    return _normalize_table(parsed, parsed_date, store, machine_name)
    return pd.DataFrame()


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [str(c[-1]) for c in out.columns]
    else:
        out.columns = [str(c) for c in out.columns]
    return out


def _normalize_table(table: pd.DataFrame, parsed_date: date, store: str, machine_name: str) -> pd.DataFrame:
    out = table.copy()
    out["date"] = parsed_date
    out["store"] = store
    if "機種名" not in out.columns:
        out["machine_name"] = machine_name
    rename = {"台番号": "machine_number", "G数": "games", "差枚": "difference_medals", "BB": "bb", "RB": "rb"}
    out = out.rename(columns=rename)
    if "機種名" in out.columns:
        out["machine_name"] = out["機種名"].astype(str).str.strip()
    out["machine_number"] = out["machine_number"].astype(str)
    for col in ["games", "difference_medals", "bb", "rb"]:
        out[col] = out[col].map(_to_int)
    return out[["date", "store", "machine_name", "machine_number", "games", "bb", "rb", "difference_medals"]]


def _to_int(value: object) -> int:
    text = str(value).replace(",", "").replace("+", "").strip()
    if text in {"", "-", "nan", "None"}:
        return 0
    m = re.search(r"-?\d+", text)
    return int(m.group(0)) if m else 0
