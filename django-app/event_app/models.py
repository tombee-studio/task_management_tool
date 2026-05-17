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
  previous_event = models.OneToOneField(
    "Event", 
    null=True, 
    blank=True,
    on_delete=models.SET_NULL,
    related_name="next_event")
  inventory = models.ManyToManyField(
    "Inventory",
    null=True, 
    blank=True,
    through="EventInventoryRelation",
    related_name="events"
  )
  
  def get_previous_difference(event):
    """
    入力されたイベント(Event)と前回のイベントをそれぞれ出力します。
    Args:
        event (Event): イベント

    Returns:
        list(Inventory): Inventoryをリスト出力
    """
    previous_event = event.previous_event

    current_relations = EventInventoryRelation.objects.filter(
        event=event
    )

    previous_relations = EventInventoryRelation.objects.filter(
        event=previous_event
    )
    
    inventory_filter = models.Q(events=event)
    if previous_event:
        inventory_filter |= models.Q(events=previous_event)

    inventories = Inventory.objects.filter(inventory_filter).distinct()
    inventories = inventories.annotate(
        current_case_count=models.Subquery(
            current_relations.values('case_count')[:1]
        ),
        current_item_count=models.Subquery(
            current_relations.values('item_count')[:1]
        ),
    )
    if previous_event:
      inventories.annotate(
        previous_case_count=models.Subquery(
            previous_relations.values('case_count')[:1]
        ),
        previous_item_count=models.Subquery(
            previous_relations.values('item_count')[:1]
        ),
      )
    return inventories


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
  
  def __str__(self):
      return f"{self.company} {self.name}"
  


class EventInventoryRelation(models.Model):
  class Meta:
    unique_together = ('event', 'inventory')

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
