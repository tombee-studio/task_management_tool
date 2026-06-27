"""SQS -> ECS dispatcher Lambda.

Reads task_id from SQS message and launches the claude-agent ECS Fargate task,
passing secrets as container environment overrides.

The agent is a one-shot, must-complete job (it edits code, commits, and pushes),
so it runs on on-demand FARGATE rather than FARGATE_SPOT -- Spot capacity can be
reclaimed mid-run ("Your Spot Task was interrupted"), leaving the work unfinished.
"""
import json
import os
import boto3

ecs = boto3.client("ecs")


def handler(event, context):
    cluster = os.environ["ECS_CLUSTER"]
    task_def = os.environ["ECS_TASK_DEFINITION"]

    # Subnet IDs are required for Fargate tasks running in awsvpc network mode.
    # They are passed as a comma-separated string from the Lambda environment.
    raw_subnets = os.environ.get("PRIVATE_SUBNET_IDS", "")
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
                {"capacityProvider": "FARGATE", "weight": 1},
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
