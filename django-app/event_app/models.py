from django.db import models
from task_app.models import Project


class Event(models.Model):
  name = models.CharField(max_length=128, default="", blank=True)
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  event_date = models.DateField(blank=False)
  participant_count = models.IntegerField(null=True, blank=True)
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

  def __str__(self):
    return f"{self.event_date} {self.name}" if self.name else str(self.event_date)


class Inventory(models.Model):
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  name = models.CharField(max_length=128, default="", blank=True)
  event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True)
  items = models.ManyToManyField(
    "Item",
    blank=True,
    through="InventoryItemRelation",
    related_name="inventory"
  )
  previous_inventory = models.OneToOneField(
    "Inventory", 
    null=True, 
    blank=True,
    on_delete=models.SET_NULL,
    related_name="next_inventory")
  
  def __str__(self):
      return f"{self.name}"
  
  def get_previous_difference(self):
    """
    入力されたイベント(Event)と前回のイベントをそれぞれ出力します。
    Returns:
        list(Inventory): Inventoryをリスト出力
    """
    previous_inventory = self.previous_inventory
    current_relations = InventoryItemRelation.objects.filter(
        inventory=self,
        item=models.OuterRef('pk'),
    )
    previous_relations = InventoryItemRelation.objects.filter(
        inventory=previous_inventory,
        item=models.OuterRef('pk'),
    )
    
    item_filter = models.Q(inventory=self)
    if previous_inventory:
        item_filter |= models.Q(inventory=previous_inventory)

    items = Item.objects.filter(item_filter).distinct()
    items = items.annotate(
        current_case_count=models.Subquery(
            current_relations.values('case_count')[:1]
        ),
        current_item_count=models.Subquery(
            current_relations.values('item_count')[:1]
        ),
    )
    if previous_inventory:
      items = items.annotate(
        previous_case_count=models.Subquery(
            previous_relations.values('case_count')[:1]
        ),
        previous_item_count=models.Subquery(
            previous_relations.values('item_count')[:1]
        ),
      )
    return items


class Item(models.Model):
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  
  company = models.CharField(max_length=128, blank=True)
  name = models.CharField(max_length=128, blank=True)
  count_per_case = models.IntegerField(blank=True, default=1)
  
  def __str__(self):
      return f"{self.company} {self.name}"
  

class InventoryItemRelation(models.Model):
  class Meta:
    unique_together = ('item', 'inventory')

  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)

  item = models.ForeignKey(
    Item, 
    on_delete=models.CASCADE, 
    null=False, 
    blank=False)
  inventory = models.ForeignKey(
    Inventory, 
    on_delete=models.CASCADE, 
    null=False, 
    blank=False)
  case_count = models.IntegerField(null=True, blank=True)
  item_count = models.IntegerField(null=True, blank=True)
