# Data Ingestion IaC — MongoDB Atlas → Snowflake

A reproducible pipeline that ingests open datasets into **MongoDB Atlas**, then replicates to **Snowflake** using [dlt](https://dlthub.com) and Terraform.

```
Open Dataset (Parquet / JSON.GZ)
        │
        ▼  Pipeline 1 (dlt)
  MongoDB Atlas
        │
        ▼  Pipeline 2 (dlt)
    Snowflake
```

---

## Datasets

| | Dataset | Format | Size | Why |
|---|---|---|---|---|
| **Simple / flat** | [NYC Yellow Taxi Trips (Jan 2024)](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) | Parquet | ~2.96 M rows, 50 MB | Completely flat schema — great for baseline benchmarking |
| **Nested / unstructured** | [GitHub Archive (GH events)](https://www.gharchive.org/) | JSON.GZ (1 file/hour) | ~100–300 K events/hour | Deeply nested: `actor`, `repo`, `payload` with commits/PRs/issues sub-documents |

> **MongoDB Atlas M0 (free tier) storage cap: 512 MB.**
> The pipelines default to **500 K taxi rows** and **4 hours of GH events** (~300 K).
> To load the full 3 M rows you need an M2+ cluster ($9/mo) or run multiple batches and flush between them.

---

## Repository structure

```
mongodb-snowflake-dlt-pipeline/
├── terraform/
│   ├── mongodb_atlas/          # DB user + IP access for your existing M0 cluster
│   └── snowflake/              # Database, schemas, warehouse, role, service user
├── pipelines/
│   ├── .dlt/
│   │   ├── config.toml         # Non-secret dlt settings
│   │   └── secrets.toml.example  ← copy to secrets.toml
│   ├── 01_load_to_mongodb/
│   │   ├── nyc_taxi_pipeline.py        # Simple dataset → MongoDB
│   │   └── github_archive_pipeline.py  # Nested dataset → MongoDB
│   └── 02_replicate_to_snowflake/
│       └── mongodb_to_snowflake.py     # MongoDB → Snowflake
├── requirements.txt
├── .gitignore
└── README.md  ← you are here
```

---

## Prerequisites

- Python 3.11+
- [Terraform CLI](https://developer.hashicorp.com/terraform/install) >= 1.5
- A MongoDB Atlas account with an existing **free M0 cluster** (you said you have one)
- A Snowflake free trial account
- Git

---

## Step-by-step guide

### Prerequisites
```bash
# Mac
brew install python@3.11
brew tap hashicorp/tap && brew install hashicorp/tap/terraform
```

### Step 1 — Clone and set up Python

```bash
git clone <your-repo-url>
cd mongodb-snowflake-dlt-pipeline

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

---

### Step 2 — Get your MongoDB Atlas API keys

1. Log in to [cloud.mongodb.com](https://cloud.mongodb.com)
2. Click your organisation name (top-left) → **Access Manager** → **API Keys**
3. Click **Create API Key**
   - Description: `terraform-dlt`
   - Permission: **Project Owner**
4. Copy the **Public Key** and **Private Key** — you won't see the private key again
5. On the next screen, add your current IP to the API key access list

Also note your **Project ID**:
- Atlas UI → your project → **Project Settings** → copy **Project ID**

And your **cluster name** (default is `Cluster0`).

---

### Step 3 — Provision MongoDB Atlas resources with Terraform

```bash
cd terraform/mongodb_atlas

cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — fill in atlas_public_key, atlas_private_key,
# atlas_project_id, db_password, and your current IP (run: curl ifconfig.me)

terraform init
terraform plan    # review what will be created
terraform apply   # creates the DB user + IP access rule
```

This creates:
- A database user `dlt_pipeline_user` with `readWriteAnyDatabase`
- An IP access list entry for your machine

After apply, copy the `connection_string_srv` output:
```bash
terraform output -raw connection_string_srv
```
Save this — you'll need it in Step 6.

---

### Step 4 — Get your Snowflake account identifier

1. Log in to [app.snowflake.com](https://app.snowflake.com)
2. Click the account menu (bottom-left corner)
3. Hover your account → click **Copy account identifier**
   - Format: `orgname-accountname` (e.g. `myorg-ab12345`)

---

### Step 5 — Provision Snowflake resources with Terraform

```bash
cd ../../terraform/snowflake

cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — fill in snowflake_account, your admin credentials,
# and choose a password for the new dlt service user

terraform init
terraform plan
terraform apply
```

This creates:
- Database `DLT_INGEST`
- Schemas `NYC_TAXI` and `GITHUB_ARCHIVE`
- Warehouse `DLT_WH` (X-Small, auto-suspends after 60 s idle)
- Role `DLT_ROLE` with scoped permissions
- Service user `DLT_USER`

---

### Step 6 — Configure dlt secrets

```bash
cd ../../pipelines/.dlt

cp secrets.toml.example secrets.toml
```

Edit `secrets.toml`:

```toml
[sources.mongodb]
connection_string = "mongodb+srv://dlt_pipeline_user:YourPassword@cluster0.xxxxx.mongodb.net"
# paste the output from Step 3

[destination.snowflake.credentials]
database  = "DLT_INGEST"
password  = "DltPipelinePass123!"   # the dlt_sf_password you set in Step 5
username  = "DLT_USER"
host      = "myorg-ab12345.snowflakecomputing.com"
warehouse = "DLT_WH"
role      = "DLT_ROLE"
```

The `host` is your Snowflake account identifier + `.snowflakecomputing.com`

---

### Step 7 — Load the simple dataset (NYC Taxi → MongoDB)

```bash
cd ../01_load_to_mongodb

# Default: loads 500,000 rows (safe for M0 free tier)
python nyc_taxi_pipeline.py

# To load more rows (M2+ only):
MAX_ROWS=3000000 python nyc_taxi_pipeline.py

# To load all rows with no limit:
MAX_ROWS=0 python nyc_taxi_pipeline.py
```

Expected output:
```
Downloading yellow_tripdata_2024-01.parquet ...
  100.0%
Yielded 10,000 rows so far...
...
Yielded 500,000 rows so far...
Load package ... loaded to destination mongodb
Done! Check your Atlas cluster > Browse Collections > nyc_taxi.yellow_taxi_trips
```

Verify in Atlas UI:
- **Browse Collections** → `nyc_taxi` → `yellow_taxi_trips`
- You should see flat documents with fields like `fare_amount`, `trip_distance`, `tpep_pickup_datetime`

---

### Step 8 — Load the nested dataset (GitHub Archive → MongoDB)

```bash
# Default: 4 hours of events (~150–300 K documents)
python github_archive_pipeline.py

# To load more hours (each hour ~50–150 K events):
GH_HOURS=24 python github_archive_pipeline.py

# To use a different date:
GH_ARCHIVE_DATE=2024-03-01 GH_HOURS=8 python github_archive_pipeline.py
```

Verify in Atlas UI:
- Browse Collections → `github_archive` → `github_events`
- Open any document — notice the nested `actor`, `repo`, and `payload` sub-documents
- `payload` structure varies by event `type` (PushEvent, PullRequestEvent, IssuesEvent, etc.)

---

### Step 9 — Replicate MongoDB → Snowflake

```bash
cd ../02_replicate_to_snowflake
python mongodb_to_snowflake.py
```

What dlt does automatically:
- Reads both MongoDB collections
- Infers Snowflake-compatible schemas from BSON types
- Flattens nested sub-documents into separate child tables:
  - `GITHUB_EVENTS__PAYLOAD__COMMITS` (array of commits per push event)
  - `GITHUB_EVENTS__PAYLOAD__PULL_REQUEST` (PR metadata)
- Writes to `DLT_INGEST.NYC_TAXI` and `DLT_INGEST.GITHUB_ARCHIVE`

Verify in Snowflake:
```sql
-- Simple flat table
SELECT COUNT(*), AVG(fare_amount), AVG(trip_distance)
FROM DLT_INGEST.NYC_TAXI.YELLOW_TAXI_TRIPS;

-- Nested events (parent table)
SELECT type, COUNT(*) as event_count
FROM DLT_INGEST.GITHUB_ARCHIVE.GITHUB_EVENTS
GROUP BY type
ORDER BY event_count DESC;

-- Child table auto-created by dlt from nested payload.commits array
SELECT *
FROM DLT_INGEST.GITHUB_ARCHIVE.GITHUB_EVENTS__PAYLOAD__COMMITS
LIMIT 10;
```

---

### Step 10 — Run incremental replication (re-run safely)

The GitHub Archive pipeline uses `created_at` as an incremental cursor. Re-running Pipeline 2 only fetches events newer than the last successful run — no duplicates, no full re-scans.

```bash
# Run again — dlt fetches only new data
python mongodb_to_snowflake.py
```

---

## Scaling to the full 3 M rows

| Tier | Storage | Approach |
|---|---|---|
| Atlas M0 (free) | 512 MB | Load in batches: 500 K rows → replicate → truncate collection → repeat |
| Atlas M2 ($9/mo) | 2 GB | Load all 3 M rows in one run |
| Atlas M10+ ($57/mo) | 10 GB+ | No changes needed |

For the batch-flush approach on M0, after each Pipeline 2 run you can drop the MongoDB collection:
```python
from pymongo import MongoClient
client = MongoClient("your_connection_string")
client["nyc_taxi"]["yellow_taxi_trips"].drop()
# Then run the next batch
```

---

## Tear down

```bash
# Remove Snowflake resources
cd terraform/snowflake && terraform destroy

# Remove MongoDB Atlas DB user and IP rule
cd ../mongodb_atlas && terraform destroy
# Note: Terraform cannot destroy M0 free clusters; delete via Atlas UI if needed
```

---

## Troubleshooting

**`MongoServerError: connection timed out`**
→ Your IP has changed. Update `allowed_ip` in `terraform/mongodb_atlas/terraform.tfvars` and re-run `terraform apply`.

**`Snowflake: JWT token is invalid`**
→ Check your `host` in `secrets.toml` — it must be `<account-id>.snowflakecomputing.com` with no trailing slash.

**`dlt: destination mongodb not found`**
→ Run `pip install "dlt[mongodb]"`. The MongoDB destination is a community extra.

**Atlas M0 storage full**
→ Drop collections you've already replicated to Snowflake, then load the next batch.
