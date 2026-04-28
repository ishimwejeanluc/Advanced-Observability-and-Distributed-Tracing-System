variable "aws_region" {
  description = "The AWS region to deploy the infrastructure in."
  type        = string
  default     = "eu-west-1"
}

variable "instance_type" {
  description = "The type of EC2 instance to launch."
  type        = string
  default     = "t3.large"
}

variable "project_name" {
  description = "Project name used for naming cloud resources"
  type        = string
  default     = "webapp"
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH into EC2"
  type        = string
  default     = "0.0.0.0/0"
}

variable "key_name" {
  description = "The name of the EC2 key pair to use for SSH access."
  type        = string
  default     = "devops-lab"

}
variable "cloudtrail_bucket_name" {
  description = "Name of the S3 bucket for CloudTrail logs"
  type        = string
  default = "web-app-cloudtrail-logs"
}
