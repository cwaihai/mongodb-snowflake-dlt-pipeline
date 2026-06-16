"""
Pipeline 2 — MongoDB Atlas → Snowflake (replication)

Reads every collection from the MongoDB databases loaded in step 1 and
replicates them to Snowflake using dlt's verified MongoDB source.

dlt handles:
  • Schema inference from MongoDB BSON documents
  • Flattening of nested sub-documents into child tables (e.g. payload__commits)
  • Incremental loading via cursor fields to avoid full re-scans
  • Type coercion to Snowflake-compatible column types

Run after Pipeline 1 has finished loading data to MongoDB.
"""

import os
import dlt
from dlt.sources.mongodb import mongodb, mongodb_collection

# ── Which MongoDB databases / collections to replicate ────────────────────────
# Matches the dataset_name values used in Pipeline 1.
DATABASES_TO_REPLICATE = {
    "nyc_taxi": {
        "collections": ["yellow_taxi_trips"],
        # tpep_pickup_datetime is a good cursor for incremental runs
        "incremental_cursor": None,   # set to "tpep_pickup_datetime" for incremental
        "snowflake_schema": "NYC_TAXI",
    },
    "github_archive": {
        "collections": ["github_events"],
        "incremental_cursor": "created_at",   # ISO timestamp — enables incremental loads
        "snowflake_schema": "GITHUB_ARCHIVE",
    },
}


def replicate_database(
    db_name: str,
    collections: list[str],
    incremental_cursor: str | None,
    snowflake_schema: str,
) -> None:
    """Replicate one MongoDB database to its corresponding Snowflake schema."""

    # Build dlt sources for each collection
    sources = []
    for col_name in collections:
        if incremental_cursor:
            # Incremental: only fetch new/updated documents since last run
            source = mongodb_collection(
                database=db_name,
                collection=col_name,
                incremental=dlt.sources.incremental(
                    incremental_cursor,
                    initial_value="2024-01-01T00:00:00Z",
                ),
            )
        else:
            # Full replacement: re-load all documents each run
            source = mongodb_collection(
                database=db_name,
                collection=col_name,
            ).with_resources(col_name)

        sources.append(source)

    pipeline = dlt.pipeline(
        pipeline_name=f"mongodb_{db_name}_to_snowflake",
        destination="snowflake",
        dataset_name=snowflake_schema,   # Snowflake schema to write into
    )

    print(f"\nReplicating MongoDB '{db_name}' → Snowflake schema '{snowflake_schema}'...")
    load_info = pipeline.run(sources)
    print(load_info)

    # Print row counts
    with pipeline.sql_client() as client:
        for col in collections:
            try:
                with client.execute_query(f'SELECT COUNT(*) FROM "{col}"') as cur:
                    count = cur.fetchone()[0]
                    print(f"  {snowflake_schema}.{col.upper()}: {count:,} rows")
            except Exception as e:
                print(f"  Could not count {col}: {e}")


def run():
    print("=" * 60)
    print("MongoDB Atlas → Snowflake Replication")
    print("=" * 60)

    for db_name, cfg in DATABASES_TO_REPLICATE.items():
        replicate_database(
            db_name=db_name,
            collections=cfg["collections"],
            incremental_cursor=cfg["incremental_cursor"],
            snowflake_schema=cfg["snowflake_schema"],
        )

    print("\nAll databases replicated. Verify in Snowflake:")
    print("  SELECT COUNT(*) FROM DLT_INGEST.NYC_TAXI.YELLOW_TAXI_TRIPS;")
    print("  SELECT COUNT(*) FROM DLT_INGEST.GITHUB_ARCHIVE.GITHUB_EVENTS;")
    print("\nFor nested GitHub events, dlt creates child tables like:")
    print("  GITHUB_ARCHIVE.GITHUB_EVENTS__PAYLOAD__COMMITS")
    print("  GITHUB_ARCHIVE.GITHUB_EVENTS__PAYLOAD__PULL_REQUEST")


if __name__ == "__main__":
    run()
