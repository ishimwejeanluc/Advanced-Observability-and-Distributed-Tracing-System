terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket         = "devops-lab-123456"
    key            = "terraform.tfstate"
    region         = "eu-west-1"
    dynamodb_table = "devops-lab-locks-123456"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = ">= 4.0"
    }
    local = {
      source  = "hashicorp/local"
      version = ">= 2.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

locals {
  ssh_user         = "ec2-user"
  private_key_path = abspath("${path.module}/../ansible/${var.key_name}.pem")
  inventory_path   = abspath("${path.module}/../ansible/inventory.ini")
  inventory_tmpl   = abspath("${path.module}/../ansible/inventory.tmpl")
}

# --- CloudWatch Module ---
module "cloudwatch" {
  source       = "./modules/cloudwatch"
  project_name = var.project_name
}

# --- Single Consolidated EC2 Module ---
module "web_server" {
  source = "./modules/ec2"

  project_name         = var.project_name
  instance_type        = var.instance_type
  key_name             = var.key_name
  allowed_ssh_cidr     = var.allowed_ssh_cidr
  iam_instance_profile = module.cloudwatch.instance_profile_name
  
  private_key_path = local.private_key_path
  inventory_path   = local.inventory_path
  template_path    = local.inventory_tmpl
  ssh_user         = local.ssh_user

  tags = {
    Name = "${var.project_name}-web"
  }
}

# --- CloudTrail Module ---
module "cloudtrail" {
  source      = "./modules/cloudtrail"
  bucket_name = var.cloudtrail_bucket_name
  account_id  = data.aws_caller_identity.current.account_id
}

# --- GuardDuty Module ---
module "guardduty" {
  source = "./modules/guardduty"
}
