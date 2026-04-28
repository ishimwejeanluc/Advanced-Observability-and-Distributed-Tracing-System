variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "webapp"
}

variable "log_group_name" {
  description = "CloudWatch Log Group name"
  type        = string
  default     = "/docker/web-app"
}

variable "retention_days" {
  description = "Number of days to retain logs"
  type        = number
  default     = 14
}
