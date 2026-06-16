output "connection_string_srv" {
  description = "SRV connection string for the cluster (use in dlt secrets)"
  value       = replace(
    data.mongodbatlas_cluster.existing.connection_strings[0].standard_srv,
    "mongodb+srv://",
    "mongodb+srv://${mongodbatlas_database_user.dlt_user.username}:${var.db_password}@"
  )
  sensitive = true
}

output "db_username" {
  description = "Created database username"
  value       = mongodbatlas_database_user.dlt_user.username
}
