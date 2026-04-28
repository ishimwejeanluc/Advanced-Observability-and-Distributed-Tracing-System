# -------------------------
# CloudWatch Logs for Docker
# -------------------------

# IAM Role for EC2 to push logs to CloudWatch
resource "aws_iam_role" "ec2_cwlogs" {
  name               = "${var.project_name}-ec2-cwlogs-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "cwlogs" {
  role       = aws_iam_role.ec2_cwlogs.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

resource "aws_iam_instance_profile" "ec2_cwlogs" {
  name = "${var.project_name}-ec2-cwlogs-profile"
  role = aws_iam_role.ec2_cwlogs.name
}

# Log group for Docker container logs
resource "aws_cloudwatch_log_group" "app" {
  name              = var.log_group_name
  retention_in_days = var.retention_days
}
