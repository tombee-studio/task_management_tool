import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "task_management.settings")

from django.core.wsgi import get_wsgi_application
import serverless_wsgi

application = get_wsgi_application()


def handler(event, context):
    return serverless_wsgi.handle_request(application, event, context)
