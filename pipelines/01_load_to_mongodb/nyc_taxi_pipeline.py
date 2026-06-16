"""
Pipeline 1a — NYC Yellow Taxi → MongoDB Atlas
Dataset: NYC TLC Yellow Taxi Trip Records (Jan 2024)
  ~2.96 M rows, flat Parquet, ~50 MB download
  Source: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

Free-tier note:
  MongoDB Atlas M0 has a 512 MB storage cap.
  MAX_ROWS defaults to 500_000 (≈ 150–200 MB in BSON).
  Remove the limit or increase it if you upgrade to M2+.
"""

import os
import dlt
import pyarrow.parquet as pq
import requests
from typing import Iterator

# ── Configuration ──────────────────────────────────────────────────────────────
PARQUET_URL = (
    "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet"
)
LOCAL_FILE = "yellow_tripdata_2024-01.parquet"
MAX_ROWS = int(os.getenv("MAX_ROWS", 500_000))   # set to 0 for no limit
BATCH_SIZE = 10_000                               # rows per dlt batch


def download_if_needed(url: str, dest: str) -> None:
    if os.path.exists(dest):
        print(f"  Using cached file: {dest}")
        return
    print(f"  Downloading {url} ...")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):  # 1 MB chunks
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  {pct:.1f}%", end="", flush=True)
    print(f"\n  Saved to {dest}")


@dlt.resource(
    name="yellow_taxi_trips",
    write_disposition="replace",   # re-running will overwrite the collection
    primary_key="_id",
)
def nyc_taxi_resource() -> Iterator[dict]:
    """Yields rows from the Parquet file in batches."""
    download_if_needed(PARQUET_URL, LOCAL_FILE)

    pf = pq.ParquetFile(LOCAL_FILE)
    yielded = 0

    for batch in pf.iter_batches(batch_size=BATCH_SIZE):
        df = batch.to_pydict()
        n = len(df[next(iter(df))])

        for i in range(n):
            if MAX_ROWS and yielded >= MAX_ROWS:
                return
            row = {col: df[col][i] for col in df}
            # Convert timestamps to ISO strings so MongoDB stores them properly
            for k, v in row.items():
                if hasattr(v, "isoformat"):
                    row[k] = v.isoformat()
            yield row
            yielded += 1

        print(f"  Yielded {yielded:,} rows so far...")


@dlt.source(name="nyc_taxi")
def nyc_taxi_source():
    return nyc_taxi_resource()


def run():
    # dlt reads MongoDB connection string from .dlt/secrets.toml
    # [sources.mongodb] connection_string = "mongodb+srv://..."
    from dlt.destinations import mongodb  # community destination

    pipeline = dlt.pipeline(
        pipeline_name="nyc_taxi_to_mongodb",
        destination=mongodb(),             # uses secrets.toml
        dataset_name="nyc_taxi",           # → MongoDB database name
    )

    print(f"Loading up to {MAX_ROWS:,} NYC taxi rows to MongoDB Atlas...")
    load_info = pipeline.run(nyc_taxi_source())
    print(load_info)
    print("\nDone! Check your Atlas cluster > Browse Collections > nyc_taxi.yellow_taxi_trips")


if __name__ == "__main__":
    run()
