"""
Pipeline 1b — GitHub Archive (nested JSON) → MongoDB Atlas
Dataset: GitHub Archive — public GitHub events as newline-delimited JSON
  Each event contains deeply nested objects:
    actor { id, login, url }
    repo  { id, name, url }
    payload { action, commits: [...], pull_request: {...}, issue: {...} }
    org   { id, login }

  Source: https://www.gharchive.org/
  Files : https://data.gharchive.org/YYYY-MM-DD-{H}.json.gz  (1 file per hour)

Free-tier note:
  Defaults to 24 hours = ~1.5–3 M events depending on the day.
  MongoDB M0 512 MB cap: set HOURS_TO_LOAD = 4 for a safe ~300 K event sample.
  Increase HOURS_TO_LOAD for paid Atlas tiers.
"""

import gzip
import json
import os
import dlt
import requests
from datetime import date, timedelta
from typing import Iterator

# ── Configuration ──────────────────────────────────────────────────────────────
ARCHIVE_DATE  = os.getenv("GH_ARCHIVE_DATE", "2024-01-15")  # YYYY-MM-DD
HOURS_TO_LOAD = int(os.getenv("GH_HOURS", "4"))             # 0–23; 4 ≈ 300 K events
DATA_DIR      = "gh_archive_data"


def download_hour_file(date_str: str, hour: int) -> str:
    """Download a single hour file from gharchive.org if not cached."""
    os.makedirs(DATA_DIR, exist_ok=True)
    filename = f"{date_str}-{hour}.json.gz"
    dest = os.path.join(DATA_DIR, filename)

    if os.path.exists(dest):
        print(f"  Using cached: {filename}")
        return dest

    url = f"https://data.gharchive.org/{filename}"
    print(f"  Downloading {url} ...")
    with requests.get(url, stream=True, timeout=60) as r:
        if r.status_code == 404:
            print(f"  Skipping (not found): {filename}")
            return None
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    print(f"  Saved: {dest}")
    return dest


def parse_event(raw: dict) -> dict:
    """
    Flatten only the top-level identifiers; keep payload nested so MongoDB
    stores the full document structure (demonstrating nested data handling).
    """
    return {
        "_id":         raw.get("id"),
        "type":        raw.get("type"),
        "created_at":  raw.get("created_at"),
        # actor — keep as nested sub-document
        "actor":       raw.get("actor", {}),
        # repo — keep as nested sub-document
        "repo":        raw.get("repo", {}),
        # org — optional nested sub-document
        "org":         raw.get("org"),
        # payload — deeply nested; structure varies by event type
        "payload":     raw.get("payload", {}),
        "public":      raw.get("public", True),
    }


@dlt.resource(
    name="github_events",
    write_disposition="replace",
    primary_key="_id",
)
def github_archive_resource() -> Iterator[dict]:
    """Streams events from hourly GitHub Archive files."""
    total = 0
    for hour in range(HOURS_TO_LOAD):
        path = download_hour_file(ARCHIVE_DATE, hour)
        if not path:
            continue

        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    yield parse_event(raw)
                    total += 1
                except json.JSONDecodeError:
                    continue

        print(f"  Total events yielded after hour {hour}: {total:,}")


@dlt.source(name="github_archive")
def github_archive_source():
    return github_archive_resource()


def run():
    from dlt.destinations import mongodb

    pipeline = dlt.pipeline(
        pipeline_name="github_archive_to_mongodb",
        destination=mongodb(),
        dataset_name="github_archive",   # → MongoDB database name
    )

    print(
        f"Loading GitHub Archive events for {ARCHIVE_DATE}, "
        f"hours 0–{HOURS_TO_LOAD - 1} → MongoDB Atlas..."
    )
    load_info = pipeline.run(github_archive_source())
    print(load_info)
    print(
        "\nDone! Check Atlas > Browse Collections > github_archive.github_events\n"
        "Notice the nested 'actor', 'repo', and 'payload' sub-documents."
    )


if __name__ == "__main__":
    run()
