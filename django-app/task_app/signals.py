import json
import os
import secrets
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Task, Comment, UserPreferences, Project
from .rules import process_task_rules


def _send_task_to_sqs(task_id, reporter_id=None):
    queue_url = os.environ.get("SQS_QUEUE_URL", "")
    if not queue_url:
        return
    import boto3
    body = {"task_id": task_id}
    if reporter_id:
        body["reporter_id"] = reporter_id
    boto3.client("sqs").send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(body),
    )


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


@receiver(pre_save, sender=Task)
def task_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_assignee_id = Task.objects.get(pk=instance.pk).assignee_id
        except Task.DoesNotExist:
            instance._prev_assignee_id = None
    else:
        instance._prev_assignee_id = None


@receiver(post_save, sender=Task)
def task_saved(sender, instance, created, **kwargs):
    try:
        process_task_rules(instance)
    except Exception:
        pass
    if not created:
        try:
            automation = User.objects.filter(username='Automation').first()
            prev_id = getattr(instance, '_prev_assignee_id', None)
            if (automation
                    and instance.assignee_id == automation.pk
                    and prev_id != automation.pk):
                _send_task_to_sqs(instance.pk, reporter_id=prev_id)
        except Exception:
            pass


@receiver(post_save, sender=Project)
def add_automation_to_project(sender, instance, created, **kwargs):
    automation = User.objects.filter(username='Automation').first()
    if automation:
        instance.participants.add(automation)


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
