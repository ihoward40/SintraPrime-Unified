terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.0" }
  }
}

provider "google" {
  project = var.gcp_project
  region = var.gcp_region
}

module "gke" {
  source = "./modules/gke"
  project_id = var.gcp_project
  region = var.gcp_region
  cluster_name = "sintraprime-cluster"
}

module "cloudsql" {
  source = "./modules/cloudsql"
  project_id = var.gcp_project
  region = var.gcp_region
  instance_name = "sintraprime-db"
}

output "kubernetes_cluster_host" { value = module.gke.endpoint }
output "cloud_sql_instance" { value = module.cloudsql.instance_id }
