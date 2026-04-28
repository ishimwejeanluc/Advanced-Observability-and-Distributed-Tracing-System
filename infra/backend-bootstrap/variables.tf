variable "aws_region" {
  description = "AWS region for backend bootstrap resources"
  type        = string
  default     = "eu-west-1"
}

variable "s3_bucket_name" {
  description = "S3 bucket name for Terraform state"
  type        = string
  default = "devops-lab-123456"
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name for Terraform state locking"
  type        = string
    default = "devops-lab-locks-123456"
}
