import secrets
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Task, Comment, UserPreferences
from .rules import process_task_rules


def generate_api_key():
    return secrets.token_urlsafe(32)


@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    if created:
        from .widget_loader import DEFAULT_WIDGET_CONFIG
        UserPreferences.objects.get_or_create(
            user=instance,
            defaults={'config': DEFAULT_WIDGET_CONFIG, 'api_key': generate_api_key()},
        )


@receiver(post_save, sender=Task)
def task_saved(sender, instance, created, **kwargs):
    # Run rule processing whenever a task is saved
    try:
        process_task_rules(instance)
    except Exception:
        # Keep signals resilient; don't bubble exceptions
        pass


@receiver(post_save, sender=Comment)
def comment_saved(sender, instance, created, **kwargs):
    # When a comment is posted on a task, process rules using the comment text
    if not instance.task:
        return
    try:
        process_task_rules(instance.task, text=instance.description)
    except Exception:
        pass
    if created:
        Task.objects.filter(pk=instance.task.pk).update(updated_at=timezone.now())
