terraform {
  required_providers {
    snowflake = {
      source  = "snowflakedb/snowflake"
      version = "~> 2.16"
    }
  }
  required_version = ">= 1.5"
}

provider "snowflake" {
  organization_name = var.snowflake_organization_name
  account_name      = var.snowflake_account_name
  user              = var.snowflake_admin_user
  private_key       = trimspace(file(var.snowflake_admin_private_key_path))
  private_key_passphrase = var.snowflake_admin_private_key_passphrase
  role              = "SYSADMIN"
}

# ── Warehouse ──────────────────────────────────────────────────────────────────
resource "snowflake_warehouse" "dlt_wh" {
  name           = "DLT_WH"
  warehouse_size = "X-SMALL"
  auto_suspend   = 60   # suspend after 60 seconds idle (saves credits)
  auto_resume    = true
  initially_suspended = true
}

# ── Database ───────────────────────────────────────────────────────────────────
resource "snowflake_database" "dlt_db" {
  name    = "DLT_INGEST"
  comment = "Database for dlt pipeline ingestion"
}

# ── Schemas ────────────────────────────────────────────────────────────────────
resource "snowflake_schema" "nyc_taxi" {
  database = snowflake_database.dlt_db.name
  name     = "NYC_TAXI"
  comment  = "NYC Yellow Taxi trip data (simple/flat)"
}

resource "snowflake_schema" "github_archive" {
  database = snowflake_database.dlt_db.name
  name     = "GITHUB_ARCHIVE"
  comment  = "GitHub Archive events (nested JSON)"
}

# ── Service role ───────────────────────────────────────────────────────────────
resource "snowflake_account_role" "dlt_role" {
  name    = "DLT_ROLE"
  comment = "Role for dlt pipeline service account"
}
resource "snowflake_grant_privileges_to_account_role" "wh_usage" {
  account_role_name = snowflake_account_role.dlt_role.name
  privileges = ["USAGE", "OPERATE"]
  on_account_object {
    object_type = "WAREHOUSE"
    object_name = snowflake_warehouse.dlt_wh.name
  }
}
resource "snowflake_grant_privileges_to_account_role" "db_usage" {
  account_role_name = snowflake_account_role.dlt_role.name
  privileges = ["USAGE", "CREATE SCHEMA"]
  on_account_object {
    object_type = "DATABASE"
    object_name = snowflake_database.dlt_db.name
  }
}
resource "snowflake_grant_privileges_to_account_role" "schema_all" {
  for_each          = toset([snowflake_schema.nyc_taxi.name, snowflake_schema.github_archive.name])
  account_role_name = snowflake_account_role.dlt_role.name
  privileges        = ["USAGE", "CREATE TABLE", "CREATE VIEW", "CREATE STAGE"]
  on_schema {
    schema_name = "\"${snowflake_database.dlt_db.name}\".\"${each.value}\""
  }
}

# ── Service account user ───────────────────────────────────────────────────────
resource "snowflake_user" "dlt_user" {
  name                = var.dlt_sf_username
  password            = var.dlt_sf_password
  login_name          = var.dlt_sf_username
  display_name        = "dlt Pipeline User"
  default_role      = snowflake_account_role.dlt_role.name
  default_warehouse = snowflake_warehouse.dlt_wh.name
  default_namespace = "${snowflake_database.dlt_db.name}.${snowflake_schema.nyc_taxi.name}"
  must_change_password = false
}
resource "snowflake_grant_account_role" "dlt_user_role" {
  role_name = snowflake_account_role.dlt_role.name
  user_name = snowflake_user.dlt_user.name
}
