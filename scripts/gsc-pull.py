"""GSC Search Analytics + Index Coverage pull for lucianomori.cloud.

Reads service-account creds from ~/.gsc/sa.json (override with GSC_SA_KEY env var).
Outputs CSVs into ./data/gsc-YYYY-MM-DD/ alongside a small JSON summary.

Run:   python scripts/gsc-pull.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SITE = "sc-domain:lucianomori.cloud"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
DEFAULT_KEY = Path.home() / ".gsc" / "sa.json"
DAYS = 90


def credentials():
    key_path = Path(os.environ.get("GSC_SA_KEY", str(DEFAULT_KEY)))
    if not key_path.is_file():
        sys.exit(f"Service-account key not found at {key_path}. Set GSC_SA_KEY or place file at ~/.gsc/sa.json.")
    return service_account.Credentials.from_service_account_file(str(key_path), scopes=SCOPES)


def query(service, *, dimensions: list[str], start: str, end: str, row_limit: int = 25000):
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": dimensions,
        "rowLimit": row_limit,
    }
    return service.searchanalytics().query(siteUrl=SITE, body=body).execute()


def write_csv(path: Path, rows: list[dict], dim_names: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = dim_names + ["clicks", "impressions", "ctr", "position"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            keys = r.get("keys", [])
            w.writerow(list(keys) + [
                r.get("clicks", 0),
                r.get("impressions", 0),
                round(r.get("ctr", 0.0) * 100, 2),
                round(r.get("position", 0.0), 2),
            ])


def main():
    creds = credentials()
    sc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

    end = date.today() - timedelta(days=2)
    start = end - timedelta(days=DAYS - 1)
    out_dir = Path("data") / f"gsc-{end:%Y-%m-%d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Pulling {start} to {end} ({DAYS} days) for {SITE}")

    summary = {"site": SITE, "start": str(start), "end": str(end), "pulled_at": datetime.now().isoformat(timespec="seconds"), "counts": {}}

    pulls = [
        ("queries.csv", ["query"]),
        ("pages.csv", ["page"]),
        ("countries.csv", ["country"]),
        ("devices.csv", ["device"]),
        ("dates.csv", ["date"]),
        ("query_page.csv", ["query", "page"]),
    ]

    try:
        for filename, dims in pulls:
            res = query(sc, dimensions=dims, start=str(start), end=str(end))
            rows = res.get("rows", [])
            write_csv(out_dir / filename, rows, dims)
            summary["counts"][filename] = len(rows)
            print(f"  {filename}: {len(rows)} rows")
    except HttpError as e:
        sys.exit(f"GSC API error: {e}\n\nIf this is a 403, grant {get_sa_email()} access to the property at\nhttps://search.google.com/search-console to Settings to Users and permissions to Add user (Restricted).")

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nDone. CSVs at {out_dir.resolve()}")


def get_sa_email() -> str:
    key_path = Path(os.environ.get("GSC_SA_KEY", str(DEFAULT_KEY)))
    try:
        return json.loads(key_path.read_text())["client_email"]
    except Exception:
        return "<service account email>"


if __name__ == "__main__":
    main()
