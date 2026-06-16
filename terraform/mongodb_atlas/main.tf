terraform {
  required_providers {
    mongodbatlas = {
      source  = "mongodb/mongodbatlas"
      version = "~> 1.15"
    }
  }
  required_version = ">= 1.5"
}

provider "mongodbatlas" {
  public_key  = var.atlas_public_key
  private_key = var.atlas_private_key
}

# ── Database user ──────────────────────────────────────────────────────────────
resource "mongodbatlas_database_user" "dlt_user" {
  project_id         = var.atlas_project_id
  username           = var.db_username
  password           = var.db_password
  auth_database_name = "admin"

  roles {
    role_name     = "readWriteAnyDatabase"
    database_name = "admin"
  }

  scopes {
    name = var.cluster_name
    type = "CLUSTER"
  }
}

# ── IP Access List ─────────────────────────────────────────────────────────────
# Allow your current IP. Replace with a specific CIDR for production.
resource "mongodbatlas_project_ip_access_list" "allow_ip" {
  project_id = var.atlas_project_id
  ip_address = var.allowed_ip
  comment    = "dlt pipeline runner"
}

# ── Data (read existing free-tier cluster) ─────────────────────────────────────
# M0 free clusters cannot be created or destroyed via Terraform.
# We use a data source to reference your existing cluster.
data "mongodbatlas_cluster" "existing" {
  project_id = var.atlas_project_id
  name       = var.cluster_name
}
