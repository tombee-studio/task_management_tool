from django.db import models

from task_app.models import Project


class Event(models.Model):
  name = models.CharField(max_length=128, default="", blank=True)
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  event_date = models.DateField(blank=False)
  participant_count = models.IntegerField(blank=True)
  project = models.ForeignKey(
    Project, 
    on_delete=models.CASCADE, 
    null=False, 
    blank=False)
  previous_event = models.ForeignKey(
    "Event", 
    null=True, 
    blank=True,
    on_delete=models.SET_NULL,
    related_name="next_event")


class Inventory(models.Model):
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  
  company = models.CharField(max_length=128, blank=True)
  name = models.CharField(max_length=128, blank=True)
  count_per_case = models.IntegerField(blank=True, default=1)
  
  project = models.ForeignKey(
    Project, 
    on_delete=models.CASCADE, 
    null=False, 
    blank=False)
  
  events = models.ManyToManyField(
    Event,
    through="EventInventoryRelation",
    related_name="inventory_history")


class EventInventoryRelation(models.Model):
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)

  event = models.ForeignKey(
    Event, 
    on_delete=models.CASCADE, 
    null=False, 
    blank=False)
  inventory = models.ForeignKey(
    Inventory, 
    on_delete=models.CASCADE, 
    null=False, 
    blank=False)
  case_count = models.IntegerField(blank=True)
  item_count = models.IntegerField(blank=True)
