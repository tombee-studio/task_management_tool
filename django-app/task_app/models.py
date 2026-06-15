from django.db import models
from django.conf import settings
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog


class Project(models.Model):
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  name = models.CharField(max_length=256, null=False, blank=False)
  git_url = models.URLField(null=True, blank=True)
  dev_branch = models.CharField(max_length=100, default='develop', blank=True)
  release_branch = models.CharField(max_length=100, default='', blank=True)
  main_branch = models.CharField(max_length=100, default='main', blank=True)
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
  project = models.ForeignKey(
    'Project',
    on_delete=models.CASCADE,
    related_name='statuses',
    null=True,
    blank=True,
  )
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


class Tag(models.Model):
  name = models.CharField(max_length=64, unique=True)

  def __str__(self):
    return self.name


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
  reporter = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.SET_NULL,
      null=True,
      blank=True,
      related_name='reported_tasks',
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
  event = models.ForeignKey(
    'event_app.Event',
    on_delete=models.SET_NULL,
    related_name='tasks',
    null=True,
    blank=True)
  tags = models.ManyToManyField(
    'Tag',
    related_name='tasks',
    blank=True)
  history = AuditlogHistoryField()
  
  def __str__(self):
    return self.title

  @property
  def total_subtask_count(self):
    return self.tasks.count()

  @property
  def completed_subtask_count(self):
    return self.tasks.filter(status__is_done=True).count()

  @property
  def deadline_days_remaining(self):
    from datetime import date
    if not self.deadline:
      return None
    return (self.deadline - date.today()).days

  @property
  def is_deadline_urgent(self):
    days = self.deadline_days_remaining
    return days is not None and not self.status.is_done and days <= 1

  @property
  def is_deadline_warning(self):
    days = self.deadline_days_remaining
    return days is not None and not self.status.is_done and 2 <= days <= 3


class UserPreferences(models.Model):
  user = models.OneToOneField(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='preferences',
  )
  config = models.TextField(blank=True, default='')
  api_key = models.CharField(max_length=64, unique=True, null=True, blank=True, default=None)

  def __str__(self):
    return self.user.username


class Rule(models.Model):
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  project = models.ForeignKey(
      Project,
      on_delete=models.CASCADE
  )
  name = models.CharField(max_length=255)
  pattern = models.TextField()
  dsl_template = models.TextField()
  enabled = models.BooleanField(default=True)
  history = AuditlogHistoryField()

  def __str__(self):
    return f"{self.project.name}: {self.name}"

auditlog.register(Project)
auditlog.register(Comment)
auditlog.register(Status)
auditlog.register(Task)
auditlog.register(Rule)
auditlog.register(Tag)
