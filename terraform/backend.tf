terraform {
  backend "s3" {
    # bucket, key, region, dynamodb_table は terraform init 時に -backend-config で渡す
    # 例: terraform init \
    #   -backend-config="bucket=your-tf-state-bucket" \
    #   -backend-config="key=task-management/terraform.tfstate" \
    #   -backend-config="region=ap-northeast-1" \
    #   -backend-config="dynamodb_table=your-tf-lock-table"
    encrypt = true
  }
}
