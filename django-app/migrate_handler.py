import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "task_management.settings")

import django
from django.core.management import call_command


def handler(event, context):
    django.setup()
    call_command("migrate", interactive=False, verbosity=1)

    return {
        "statusCode": 200,
        "body": "migrate completed",
    }
