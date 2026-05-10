import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "task_management.settings")

import django
from django.contrib.auth import get_user_model


def handler(event, context):
    django.setup()

    User = get_user_model()

    username = os.environ["DJANGO_SUPERUSER_USERNAME"]
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
    password = os.environ["DJANGO_SUPERUSER_PASSWORD"]

    username_field = User.USERNAME_FIELD

    lookup = {
        username_field: username,
    }

    if User.objects.filter(**lookup).exists():
        return {
            "statusCode": 200,
            "body": "superuser already exists",
        }

    create_kwargs = {
        username_field: username,
        "email": email,
        "password": password,
    }

    user = User.objects.create_superuser(**create_kwargs)

    return {
        "statusCode": 200,
        "body": f"superuser created: {getattr(user, username_field)}",
    }