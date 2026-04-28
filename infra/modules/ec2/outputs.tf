output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.ec2_server.id
}

output "public_ip" {
  description = "Public IP of the EC2 instance"
  value       = aws_instance.ec2_server.public_ip
}

output "public_dns" {
  description = "Public DNS of the EC2 instance"
  value       = aws_instance.ec2_server.public_dns
}

output "key_name" {
  description = "Name of the key pair"
  value       = aws_key_pair.this.key_name
}

output "private_key_path" {
  description = "Path to the private key"
  value       = var.private_key_path
}

output "inventory_path" {
  description = "Path to the Ansible inventory"
  value       = var.inventory_path
}

output "security_group_id" {
  description = "ID of the security group"
  value       = aws_security_group.this.id
}