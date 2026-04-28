variable "bucket_name" {
  description = "Globally unique S3 bucket name for CloudTrail logs"
  type        = string
  default     = "web-app-cloudtrail-logs"
}

variable "account_id" {
  description = "AWS Account ID (used in S3 bucket policy)"
  type        = string
}

variable "trail_name" {
  description = "Name of the CloudTrail trail"
  type        = string
  default     = "organization-trail"
}

variable "log_expiration_days" {
  description = "Number of days before CloudTrail logs expire in S3"
  type        = number
  default     = 365
}
