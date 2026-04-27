"""GSC Search Analytics + Index Coverage pull for lucianomori.cloud.

Auth: OAuth 2.0 installed-app flow. Reads the client config from
~/.gsc/oauth.json (or $GSC_OAUTH_CLIENT). Stores the user's refresh
token at ~/.gsc/token.json (or $GSC_TOKEN) so subsequent runs are
silent. First run opens a browser for one-time consent.

Outputs CSVs into ./data/gsc-YYYY-MM-DD/ and a small JSON summary.

Run:   python scripts/gsc-pull.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SITE = "sc-domain:lucianomori.cloud"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
CLIENT_PATH = Path(os.environ.get("GSC_OAUTH_CLIENT", str(Path.home() / ".gsc" / "oauth.json")))
TOKEN_PATH = Path(os.environ.get("GSC_TOKEN", str(Path.home() / ".gsc" / "token.json")))
DAYS = 90


def credentials() -> Credentials:
    creds: Credentials | None = None
    if TOKEN_PATH.is_file():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not CLIENT_PATH.is_file():
            sys.exit(f"OAuth client config not found at {CLIENT_PATH}. Set GSC_OAUTH_CLIENT or place file at ~/.gsc/oauth.json.")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_PATH), SCOPES)
        creds = flow.run_local_server(port=0, prompt="consent", open_browser=True)

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds


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

    summary = {
        "site": SITE,
        "start": str(start),
        "end": str(end),
        "pulled_at": datetime.now().isoformat(timespec="seconds"),
        "counts": {},
    }

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
        sys.exit(f"GSC API error: {e}")

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nDone. CSVs at {out_dir.resolve()}")


if __name__ == "__main__":
    main()
