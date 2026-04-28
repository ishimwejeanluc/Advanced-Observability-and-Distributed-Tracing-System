variable "project_name" {
  description = "Project name for tagging"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  
}

variable "key_name" {
  description = "EC2 key pair name"
  type        = string
}



variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH into the instance"
  type        = string
  default     = "0.0.0.0/0"
}

variable "private_key_path" {
  description = "Path where the private key will be saved"
  type        = string
}

variable "inventory_path" {
  description = "Path where the Ansible inventory will be saved"
  type        = string
}

variable "template_path" {
  description = "Path to the Ansible inventory template"
  type        = string
}

variable "ssh_user" {
  description = "SSH user for Ansible inventory"
  type        = string
  default     = "ec2-user"
}

variable "iam_instance_profile" {
  description = "IAM instance profile name for the EC2 instance"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags for the resources"
  type        = map(string)
  default     = {}
}