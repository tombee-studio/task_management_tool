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

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
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
  default = "*"
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
# Security Groups
# -----------------------------

resource "aws_security_group" "lambda" {
  name        = "${local.name}-lambda-sg"
  description = "Security group for Django Lambda"
  vpc_id      = var.vpc_id
}

resource "aws_security_group" "rds" {
  name        = "${local.name}-rds-sg"
  description = "Security group for RDS"
  vpc_id      = var.vpc_id
}

# Lambda -> RDS
resource "aws_vpc_security_group_egress_rule" "lambda_to_rds" {
  security_group_id = aws_security_group.lambda.id

  referenced_security_group_id = aws_security_group.rds.id
  ip_protocol                  = "tcp"
  from_port                    = local.db_port
  to_port                      = local.db_port

  description = "Allow Lambda to connect to RDS"
}

# RDS <- Lambda
resource "aws_vpc_security_group_ingress_rule" "rds_from_lambda" {
  security_group_id = aws_security_group.rds.id

  referenced_security_group_id = aws_security_group.lambda.id
  ip_protocol                  = "tcp"
  from_port                    = local.db_port
  to_port                      = local.db_port

  description = "Allow RDS to receive traffic from Lambda"
}

# -----------------------------
# RDS
# -----------------------------

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_db_subnet_group" "db" {
  name       = "${local.name}-db-subnet-group"
  subnet_ids = var.private_subnet_ids
}

resource "aws_db_instance" "db" {
  identifier = "${local.name}-db"

  engine         = "postgres"
  engine_version = "16.12"

  instance_class = "db.t4g.micro"

  allocated_storage = 20
  storage_type      = "gp3"

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.db.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  publicly_accessible = false

  backup_retention_period = 1

  # 開発用
  deletion_protection = false
  skip_final_snapshot = true
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

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
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

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DJANGO_SETTINGS_MODULE = "task_management.settings"
      DJANGO_SECRET_KEY      = var.django_secret_key
      ALLOWED_HOSTS          = "${aws_api_gateway_rest_api.api.id}.execute-api.${data.aws_region.current.region}.amazonaws.com"
      DEBUG          = var.debug_mode

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
    aws_iam_role_policy_attachment.lambda_vpc,
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

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DJANGO_SETTINGS_MODULE = "task_management.settings"
      DJANGO_SECRET_KEY      = var.django_secret_key
      ALLOWED_HOSTS          = "${aws_api_gateway_rest_api.api.id}.execute-api.${data.aws_region.current.region}.amazonaws.com"
      DEBUG          = var.debug_mode

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
    aws_iam_role_policy_attachment.lambda_vpc,
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

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DJANGO_SETTINGS_MODULE = "task_management.settings"
      DJANGO_SECRET_KEY = var.django_secret_key
      ALLOWED_HOSTS = "${aws_api_gateway_rest_api.api.id}.execute-api.${data.aws_region.current.region}.amazonaws.com"

      DB_NAME = var.db_name
      DB_USER = var.db_username
      DB_PASSWORD = random_password.db.result
      DB_HOST = aws_db_instance.db.address
      DB_PORT = tostring(local.db_port)
      DB_SSL_USE  = var.db_ssl_use

      DJANGO_SUPERUSER_USERNAME = var.superuser_username
      DJANGO_SUPERUSER_EMAIL    = var.superuser_email
      DJANGO_SUPERUSER_PASSWORD = var.superuser_password
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy_attachment.lambda_vpc,
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

output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "api_url" {
  value = "https://${aws_api_gateway_rest_api.api.id}.execute-api.${data.aws_region.current.region}.amazonaws.com/${var.stage}/"
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
