variable "snowflake_account" {
  description = "Snowflake account identifier (e.g. xy12345.us-east-1 or orgname-accountname)"
  type        = string
}

variable "snowflake_admin_user" {
  description = "Your Snowflake admin username (used only for provisioning)"
  type        = string
}

variable "snowflake_admin_password" {
  description = "Your Snowflake admin password"
  type        = string
  sensitive   = true
}

variable "dlt_sf_username" {
  description = "New service account username for dlt"
  type        = string
  default     = "DLT_USER"
}

variable "dlt_sf_password" {
  description = "Password for the dlt service account"
  type        = string
  sensitive   = true
}
