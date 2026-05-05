terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project = "SintraPrime"
      Phase = "25A"
    }
  }
}

module "vpc" {
  source = "./modules/vpc"
  name_prefix = var.project_name
  cidr_block = var.vpc_cidr
}

output "alb_dns" { value = "aws-alb.example.com" }
