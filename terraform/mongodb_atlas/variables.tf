variable "atlas_public_key" {
  description = "MongoDB Atlas API public key"
  type        = string
  sensitive   = true
}

variable "atlas_private_key" {
  description = "MongoDB Atlas API private key"
  type        = string
  sensitive   = true
}

variable "atlas_project_id" {
  description = "MongoDB Atlas project ID (find in Atlas UI > Project Settings)"
  type        = string
}

variable "cluster_name" {
  description = "Name of your existing Atlas cluster"
  type        = string
  default     = "Cluster0"
}

variable "db_username" {
  description = "Database username for the dlt pipeline"
  type        = string
  default     = "dlt_pipeline_user"
}

variable "db_password" {
  description = "Database user password"
  type        = string
  sensitive   = true
}

variable "allowed_ip" {
  description = "Your public IP address (run: curl ifconfig.me)"
  type        = string
}
