output "snowflake_database" {
  value = snowflake_database.dlt_db.name
}

output "snowflake_warehouse" {
  value = snowflake_warehouse.dlt_wh.name
}

output "dlt_user" {
  value = snowflake_user.dlt_user.name
}

output "nyc_taxi_schema" {
  value = "${snowflake_database.dlt_db.name}.${snowflake_schema.nyc_taxi.name}"
}

output "github_archive_schema" {
  value = "${snowflake_database.dlt_db.name}.${snowflake_schema.github_archive.name}"
}
