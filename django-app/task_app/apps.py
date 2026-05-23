from django.apps import AppConfig


class TaskAppConfig(AppConfig):
    name = 'task_app'
    def ready(self):
        # Import signal handlers to ensure they are registered
        from . import signals  # noqa: F401
