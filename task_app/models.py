from django.db import models
from django.conf import settings
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog


class Project(models.Model):
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  name = models.CharField(max_length=256, null=False, blank=False)
  git_url = models.URLField(null=True, blank=True)
  history = AuditlogHistoryField()

  def __str__(self):
    return self.name


class Status(models.Model):
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  name = models.CharField(max_length=128, null=False, blank=False)
  is_done = models.BooleanField(default=False)
  history = AuditlogHistoryField()
  
  def __str__(self):
    return self.name


class Comment(models.Model):
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  author = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.CASCADE
  )
  description = models.TextField()
  task = models.ForeignKey(
      "Task",
      on_delete=models.CASCADE,
      null=True
  )
  history = AuditlogHistoryField()


class Task(models.Model):
  title = models.CharField(max_length=256, null=False)
  project = models.ForeignKey(
      Project,
      on_delete=models.CASCADE
  )
  description = models.TextField(default="")
  assignee = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.CASCADE
  )
  parent = models.ForeignKey(
      "Task",
      on_delete=models.CASCADE,
      related_name='tasks',
      null=True,
      blank=True
  )
  status = models.ForeignKey(
      Status,
      on_delete=models.CASCADE,
      null=False
  )
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  deadline = models.DateField(null=True, blank=True)
  completed_at = models.DateTimeField(null=True, blank=True)
  history = AuditlogHistoryField()
  
  def __str__(self):
    return self.title

auditlog.register(Project)
auditlog.register(Comment)
auditlog.register(Status)
auditlog.register(Task)
