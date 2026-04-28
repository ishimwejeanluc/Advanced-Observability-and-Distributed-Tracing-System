output "instance_public_ip" {
  description = "The public IP address of the EC2 instance."
  value       = module.web_server.public_ip
}

output "key_pair_name" {
  description = "Name of the Terraform-created key pair"
  value       = module.web_server.key_name
}

output "ansible_private_key_path" {
  description = "Path to generated private key used by Ansible"
  value       = module.web_server.private_key_path
}

output "ansible_inventory_path" {
  description = "Path to generated Ansible inventory file"
  value       = module.web_server.inventory_path
}

output "instance_public_dns" {
  description = "The public DNS name of the EC2 instance."
  value       = module.web_server.public_dns
}

output "app_url" {
  description = "Application URL on the EC2 host"
  value       = "http://${module.web_server.public_dns}:5000"
}
