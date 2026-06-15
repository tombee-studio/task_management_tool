"""SQS -> ECS dispatcher Lambda.

Reads task_id from SQS message and launches the claude-agent ECS Fargate Spot task,
passing secrets as container environment overrides.
"""
import json
import os
import boto3

ecs = boto3.client("ecs")


def handler(event, context):
    cluster = os.environ["ECS_CLUSTER"]
    task_def = os.environ["ECS_TASK_DEFINITION"]

    # Public subnet IDs are required for Fargate tasks without a VPC NAT gateway.
    # They are passed as a comma-separated string from the Lambda environment.
    raw_subnets = os.environ.get("PUBLIC_SUBNET_IDS", "")
    subnets = [s.strip() for s in raw_subnets.split(",") if s.strip()]

    secret_env = [
        {"name": "ANTHROPIC_API_KEY", "value": os.environ["ANTHROPIC_API_KEY"]},
        {"name": "GITHUB_PAT",        "value": os.environ["GITHUB_PAT"]},
        {"name": "TASK_API_KEY",      "value": os.environ["TASK_API_KEY"]},
    ]

    for record in event.get("Records", []):
        body = json.loads(record["body"])
        task_id = body["task_id"]
        reporter_id = body.get("reporter_id")

        dynamic_env = [{"name": "TASK_ID", "value": str(task_id)}]
        if reporter_id:
            dynamic_env.append({"name": "REPORTER_ID", "value": str(reporter_id)})

        ecs.run_task(
            cluster=cluster,
            taskDefinition=task_def,
            capacityProviderStrategy=[
                {"capacityProvider": "FARGATE_SPOT", "weight": 1},
            ],
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": subnets,
                    "securityGroups": [],
                    "assignPublicIp": "ENABLED",
                }
            },
            overrides={
                "containerOverrides": [{
                    "name": "claude-agent",
                    "environment": secret_env + dynamic_env,
                }]
            },
        )
        print(f"[dispatcher] Started ECS task for task_id={task_id}")
