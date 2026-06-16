terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_region" "current" {}

variable "aws_region" {
  type    = string
  default = "ap-northeast-1"
}

variable "project" {
  type    = string
  default = "django-serverless"
}

variable "stage" {
  type    = string
  default = "dev"
}

variable "db_name" {
  type    = string
  default = "djangoapp"
}

variable "db_username" {
  type    = string
  default = "django_user"
}

variable "django_secret_key" {
  type      = string
  sensitive = true
}

variable "allowed_hosts" {
  type    = string
  default = ""
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "debug_mode" {
  type    = string
  default = "False"
}

variable "superuser_username" {
  type    = string
  default = "admin"
}

variable "superuser_email" {
  type    = string
  default = "admin@example.com"
}

variable "superuser_password" {
  type      = string
  sensitive = true
}

variable "db_ssl_use" {
  type    = string
  default = "require"
}

variable "anthropic_api_key" {
  type      = string
  sensitive = true
}

variable "github_pat" {
  type      = string
  sensitive = true
}

variable "task_api_key" {
  type      = string
  sensitive = true
}

variable "task_api_url" {
  type = string
}

variable "task_status_merge_id" {
  type    = number
  default = 12
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "List of subnet IDs for ECS Fargate tasks"
  default     = []
}

locals {
  name      = "${var.project}-${var.stage}"
  db_port   = 5432
  image_uri = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
}

# -----------------------------
# ECR
# -----------------------------

resource "aws_ecr_repository" "app" {
  name = local.name

  image_scanning_configuration {
    scan_on_push = true
  }
}

# -----------------------------
# RDS
# -----------------------------

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_db_instance" "db" {
  identifier = "${local.name}-db"

  engine         = "postgres"
  engine_version = "16.13"

  instance_class = "db.t4g.micro"

  allocated_storage = 20
  storage_type      = "gp3"

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result

  publicly_accessible = true

  backup_retention_period = 1

  # 開発用
  deletion_protection = false
  skip_final_snapshot = true
}

# -----------------------------
# SQS — task automation queue
# -----------------------------

resource "aws_sqs_queue" "task_automation_dlq" {
  name                      = "${local.name}-task-automation-dlq"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "task_automation" {
  name                       = "${local.name}-task-automation"
  visibility_timeout_seconds = 900
  message_retention_seconds  = 86400

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.task_automation_dlq.arn
    maxReceiveCount     = 3
  })
}

output "task_automation_queue_url" {
  value = aws_sqs_queue.task_automation.url
}

output "task_automation_queue_arn" {
  value = aws_sqs_queue.task_automation.arn
}

# -----------------------------
# Lambda IAM Role
# -----------------------------

resource "aws_iam_role" "lambda" {
  name = "${local.name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_sqs_send" {
  name = "${local.name}-lambda-sqs-send"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sqs:SendMessage"]
      Resource = aws_sqs_queue.task_automation.arn
    }]
  })
}

# -----------------------------
# Lambda Functions
# -----------------------------

resource "aws_lambda_function" "web" {
  function_name = "${local.name}-web"
  role          = aws_iam_role.lambda.arn

  package_type = "Image"
  image_uri    = local.image_uri

  memory_size = 128
  timeout     = 30

  architectures = ["arm64"]

  environment {
    variables = {
      DJANGO_SETTINGS_MODULE = "task_management.settings"
      DJANGO_SECRET_KEY      = var.django_secret_key
      ALLOWED_HOSTS          = trimspace(var.allowed_hosts) != "" ? var.allowed_hosts : "${aws_api_gateway_rest_api.api.id}.execute-api.${data.aws_region.current.region}.amazonaws.com"
      DEBUG                  = var.debug_mode

      DB_NAME       = var.db_name
      DB_USER       = var.db_username
      DB_PASSWORD   = random_password.db.result
      DB_HOST       = aws_db_instance.db.address
      DB_PORT       = tostring(local.db_port)
      DB_SSL_USE    = var.db_ssl_use
      SQS_QUEUE_URL = aws_sqs_queue.task_automation.url
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
  ]
}

resource "aws_lambda_function" "migrate" {
  function_name = "${local.name}-migrate"
  role          = aws_iam_role.lambda.arn

  package_type = "Image"
  image_uri    = local.image_uri

  memory_size = 128
  timeout     = 300

  architectures = ["arm64"]

  image_config {
    command = ["migrate_handler.handler"]
  }

  environment {
    variables = {
      DJANGO_SETTINGS_MODULE = "task_management.settings"
      DJANGO_SECRET_KEY      = var.django_secret_key
      ALLOWED_HOSTS          = trimspace(var.allowed_hosts) != "" ? var.allowed_hosts : "${aws_api_gateway_rest_api.api.id}.execute-api.${data.aws_region.current.region}.amazonaws.com"
      DEBUG                  = var.debug_mode

      DB_NAME     = var.db_name
      DB_USER     = var.db_username
      DB_PASSWORD = random_password.db.result
      DB_HOST     = aws_db_instance.db.address
      DB_PORT     = tostring(local.db_port)
      DB_SSL_USE  = var.db_ssl_use
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
  ]
}

resource "aws_lambda_function" "createsuperuser" {
  function_name = "${local.name}-createsuperuser"
  role          = aws_iam_role.lambda.arn

  package_type  = "Image"
  image_uri     = local.image_uri
  architectures = ["arm64"]

  memory_size = 128
  timeout     = 300

  image_config {
    command = ["createsuperuser_handler.handler"]
  }

  environment {
    variables = {
      DJANGO_SETTINGS_MODULE = "task_management.settings"
      DJANGO_SECRET_KEY      = var.django_secret_key
      ALLOWED_HOSTS          = trimspace(var.allowed_hosts) != "" ? var.allowed_hosts : "${aws_api_gateway_rest_api.api.id}.execute-api.${data.aws_region.current.region}.amazonaws.com"

      DB_NAME     = var.db_name
      DB_USER     = var.db_username
      DB_PASSWORD = random_password.db.result
      DB_HOST     = aws_db_instance.db.address
      DB_PORT     = tostring(local.db_port)
      DB_SSL_USE  = var.db_ssl_use

      DJANGO_SUPERUSER_USERNAME = var.superuser_username
      DJANGO_SUPERUSER_EMAIL    = var.superuser_email
      DJANGO_SUPERUSER_PASSWORD = var.superuser_password
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
  ]
}

# -----------------------------
# API Gateway REST API
# -----------------------------

resource "aws_api_gateway_rest_api" "api" {
  name = "${local.name}-api"
}

resource "aws_api_gateway_method" "root_any" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_rest_api.api.root_resource_id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "root_lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_rest_api.api.root_resource_id
  http_method = aws_api_gateway_method.root_any.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.web.invoke_arn
}

resource "aws_api_gateway_resource" "proxy" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "proxy_any" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.proxy.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "proxy_lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.proxy.id
  http_method = aws_api_gateway_method.proxy_any.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.web.invoke_arn
}

resource "aws_lambda_permission" "allow_apigateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.web.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

resource "aws_api_gateway_deployment" "api" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_method.root_any.id,
      aws_api_gateway_integration.root_lambda.id,
      aws_api_gateway_resource.proxy.id,
      aws_api_gateway_method.proxy_any.id,
      aws_api_gateway_integration.proxy_lambda.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_integration.root_lambda,
    aws_api_gateway_integration.proxy_lambda,
  ]
}

resource "aws_api_gateway_stage" "api" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  deployment_id = aws_api_gateway_deployment.api.id
  stage_name    = var.stage
}

# -----------------------------
# ECR — claude-agent image
# -----------------------------

resource "aws_ecr_repository" "claude_agent" {
  name = "${local.name}-claude-agent"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# -----------------------------
# ECS — claude-agent (Fargate Spot)
# -----------------------------

resource "aws_ecs_cluster" "agent" {
  name = "${local.name}-agent"
}

resource "aws_ecs_cluster_capacity_providers" "agent" {
  cluster_name       = aws_ecs_cluster.agent.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
}

resource "aws_iam_role" "ecs_task_execution" {
  name = "${local.name}-ecs-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_basic" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name = "${local.name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task_sqs" {
  name = "${local.name}-ecs-task-sqs"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
      Resource = aws_sqs_queue.task_automation.arn
    }]
  })
}

resource "aws_cloudwatch_log_group" "ecs_agent" {
  name              = "/ecs/${local.name}-claude-agent"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "claude_agent" {
  family                   = "${local.name}-claude-agent"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  execution_role_arn = aws_iam_role.ecs_task_execution.arn
  task_role_arn      = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "claude-agent"
    image     = "${aws_ecr_repository.claude_agent.repository_url}:latest"
    essential = true

    environment = [
      { name = "TASK_API_URL",        value = var.task_api_url },
      { name = "TASK_API_KEY",        value = var.task_api_key },
      { name = "TASK_STAUS_MERGE_ID", value = tostring(var.task_status_merge_id) },
    ]

    secrets = []

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs_agent.name
        "awslogs-region"        = data.aws_region.current.region
        "awslogs-stream-prefix" = "agent"
      }
    }
  }])
}

# -----------------------------
# Lambda — SQS dispatcher -> ECS
# -----------------------------

resource "aws_iam_role" "lambda_dispatcher" {
  name = "${local.name}-dispatcher-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "dispatcher_basic" {
  role       = aws_iam_role.lambda_dispatcher.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "dispatcher_ecs_run" {
  name = "${local.name}-dispatcher-ecs-run"
  role = aws_iam_role.lambda_dispatcher.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecs:RunTask"]
        Resource = "${aws_ecs_task_definition.claude_agent.arn_without_revision}:*"
      },
      {
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = [
          aws_iam_role.ecs_task_execution.arn,
          aws_iam_role.ecs_task.arn,
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Resource = aws_sqs_queue.task_automation.arn
      }
    ]
  })
}

resource "aws_lambda_function" "dispatcher" {
  function_name = "${local.name}-dispatcher"
  role          = aws_iam_role.lambda_dispatcher.arn
  runtime       = "python3.12"
  handler       = "dispatcher.handler"
  filename      = "${path.module}/dispatcher.zip"
  timeout       = 30

  environment {
    variables = {
      ECS_CLUSTER         = aws_ecs_cluster.agent.arn
      ECS_TASK_DEFINITION = aws_ecs_task_definition.claude_agent.arn
      ANTHROPIC_API_KEY   = var.anthropic_api_key
      GITHUB_PAT          = var.github_pat
      TASK_API_KEY        = var.task_api_key
      PRIVATE_SUBNET_IDS  = join(",", var.private_subnet_ids)
    }
  }
}

resource "aws_lambda_event_source_mapping" "sqs_to_dispatcher" {
  event_source_arn = aws_sqs_queue.task_automation.arn
  function_name    = aws_lambda_function.dispatcher.arn
  batch_size       = 1
}

output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "api_url" {
  value = "https://${aws_api_gateway_rest_api.api.id}.execute-api.${data.aws_region.current.region}.amazonaws.com/${var.stage}/"
}

output "web_lambda_name" {
  value = aws_lambda_function.web.function_name
}

output "migrate_lambda_name" {
  value = aws_lambda_function.migrate.function_name
}

output "createsuperuser_lambda_name" {
  value = aws_lambda_function.createsuperuser.function_name
}

output "db_endpoint" {
  value = aws_db_instance.db.address
}

output "claude_agent_ecr_url" {
  value = aws_ecr_repository.claude_agent.repository_url
}

output "dispatcher_lambda_name" {
  value = aws_lambda_function.dispatcher.function_name
}
