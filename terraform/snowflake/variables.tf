variable "snowflake_organization_name" {
  description = "Snowflake organization name (the part before the dash in your account identifier, e.g. 'MYORG' from 'MYORG-AB12345')"
  type        = string
}
variable "snowflake_account_name" {
  description = "Snowflake account name (the part after the dash in your account identifier, e.g. 'AB12345' from 'MYORG-AB12345')"
  type        = string
}

variable "snowflake_admin_user" {
  description = "Your Snowflake admin username (used only for provisioning)"
  type        = string
}

variable "snowflake_admin_private_key_path" {
  description = "Path to the PEM private key file for your Snowflake admin user (key-pair auth bypasses MFA)"
  type        = string
}

variable "snowflake_admin_private_key_passphrase" {
  description = "Passphrase for the private key (leave empty if the key is unencrypted)"
  type        = string
  sensitive   = true
  default     = ""
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
