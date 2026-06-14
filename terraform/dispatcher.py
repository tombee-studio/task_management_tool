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
    subnets = os.environ["ECS_SUBNET_IDS"].split(",")
    sg = os.environ["ECS_SECURITY_GROUP"]

    secret_env = [
        {"name": "ANTHROPIC_API_KEY", "value": os.environ["ANTHROPIC_API_KEY"]},
        {"name": "GITHUB_PAT",        "value": os.environ["GITHUB_PAT"]},
        {"name": "TASK_API_KEY",      "value": os.environ["TASK_API_KEY"]},
    ]

    for record in event.get("Records", []):
        body = json.loads(record["body"])
        task_id = body["task_id"]

        ecs.run_task(
            cluster=cluster,
            taskDefinition=task_def,
            launchType="FARGATE",
            capacityProviderStrategy=[
                {"capacityProvider": "FARGATE_SPOT", "weight": 1},
            ],
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": subnets,
                    "securityGroups": [sg],
                    "assignPublicIp": "DISABLED",
                }
            },
            overrides={
                "containerOverrides": [{
                    "name": "claude-agent",
                    "environment": secret_env + [
                        {"name": "TASK_ID", "value": str(task_id)},
                    ],
                }]
            },
        )
        print(f"[dispatcher] Started ECS task for task_id={task_id}")
