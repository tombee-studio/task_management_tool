# タスク管理ツール（Task Management Tool）

## 環境構築手順

### Docker
#### dockerフォルダに移動
```:
cd docker
```

#### .env
`docker`フォルダ直下に下記内容の`.env`を作成します。

```:
DJANGO_SECRET_KEY="django secret key"
DEBUG="True"
DJANGO_LOGLEVEL=info
DJANGO_ALLOWED_HOSTS=localhost
DATABASE_ENGINE=postgresql_psycopg2
DB_NAME=dockerdjango
DB_USER=dbuser
DB_PASSWORD=dbpassword
DB_HOST=db
DB_PORT=5432
```

#### dockerを起動
```:
docker compose up -d
```

### Amazon Web Service

#### terraformフォルダに移動
```:
cd terraform
```

#### terraform.tfvarsを作成
```terraform:
# -----------------------------
# Common
# -----------------------------
project = "project name"
stage = "stage"

# -----------------------------
# Django
# -----------------------------

django_secret_key = "django secret key"
allowed_hosts = "allowed hosts"
image_tag = "image tag"

debug_mode = "True"

superuser_username = "admin"
superuser_email = "*****"
superuser_password = "*****"

# -----------------------------
# Amazon Web Service(AWS)
# -----------------------------
aws_region = "AWS Region"
vpc_id = "vpc id"

private_subnet_ids = [
  "***"
]
```

#### Amazon ECRをデプロイ
```shell:
terraform apply -target aws_ecr_repository.app
```

#### Django appをDocker containerに格納
```shell:
../django-app/
REPO_URL=$(terraform output -raw ecr_repository_url)
docker buildx build \
  --platform linux/arm64 \
  --provenance=false \
  --sbom=false \
  -t "${REPO_URL}:latest" \
  --push . \
  --no-cache
```

#### デプロイ
```shell:
../terraform/
terraform apply
```

#### DBにmigrate
```shell:
MIGRATE_FUNCTION=$(terraform output -raw migrate_lambda_name)

aws lambda invoke \
  --function-name "$MIGRATE_FUNCTION" \
  response.json

cat response.json
```

#### super userを作成
```shell:
CREATESUPERUSER_FUNCTION=$(terraform output -raw createsuperuser_lambda_name)
aws lambda invoke \                                                          
  --function-name "$CREATESUPERUSER_FUNCTION" \
  response.json
```

#### Webアプリへアクセス
```shell:
terraform output -raw api_url
```

`https://***.amazonaws.com/{stage}/` へアクセスします。
