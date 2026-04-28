output "instance_profile_name" {
  description = "IAM instance profile name to attach to EC2"
  value       = aws_iam_instance_profile.ec2_cwlogs.name
}

output "log_group_arn" {
  description = "ARN of the CloudWatch Log Group"
  value       = aws_cloudwatch_log_group.app.arn
}
