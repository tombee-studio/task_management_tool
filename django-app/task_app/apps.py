from django.apps import AppConfig


class TaskAppConfig(AppConfig):
    name = 'task_app'
    def ready(self):
        from . import signals  # noqa: F401
        from .api import openapi_extensions  # noqa: F401
