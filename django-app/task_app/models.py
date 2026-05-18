from django.db import models
from django.conf import settings
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from tree_queries.query import TreeQuerySet


class Project(models.Model):
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  name = models.CharField(max_length=256, null=False, blank=False)
  git_url = models.URLField(null=True, blank=True)
  history = AuditlogHistoryField()
  participants = models.ManyToManyField(
    settings.AUTH_USER_MODEL,
    related_name="projects",
    blank=True)

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
  progress_summary = models.CharField(default="", max_length=256, null=False, blank=True)
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
  related_tasks = models.ManyToManyField(
    "Task",
    symmetrical=True,
    blank=True)
  status = models.ForeignKey(
      Status,
      on_delete=models.CASCADE,
      null=False
  )
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  deadline = models.DateField(null=True, blank=True)
  completed_at = models.DateTimeField(null=True, blank=True)
  watched = models.ManyToManyField(
    settings.AUTH_USER_MODEL,
    related_name="watches",
    symmetrical=True,
    null=True,
    blank=True)
  history = AuditlogHistoryField()
  
  objects = TreeQuerySet.as_manager(with_tree_fields=True)
  
  def __str__(self):
    return self.title

  @property
  def total_subtask_count(self):
    return self.tasks.count()

  @property
  def completed_subtask_count(self):
    return self.tasks.filter(status__is_done=True).count()

auditlog.register(Project)
auditlog.register(Comment)
auditlog.register(Status)
auditlog.register(Task)
