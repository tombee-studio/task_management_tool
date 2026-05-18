from django.test import TestCase

from task_app.models import Project
from .models import Event, Inventory, Item, InventoryItemRelation


class EventAppModelsTest(TestCase):
    def test_get_previous_difference(self):
        project = Project.objects.create(name="Project")
        event1 = Event.objects.create(
            event_date="2026-01-01",
            participant_count=10,
            project=project,
        )
        event2 = Event.objects.create(
            event_date="2026-02-01",
            participant_count=15,
            project=project,
            previous_event=event1,
        )
        inventory1 = Inventory.objects.create(name="Inventory A", event=event1)
        inventory2 = Inventory.objects.create(
            name="Inventory B",
            event=event2,
            previous_inventory=inventory1,
        )
        item = Item.objects.create(company="Company", name="Item", count_per_case=1)
        InventoryItemRelation.objects.create(
            item=item,
            inventory=inventory1,
            case_count=2,
            item_count=10,
        )
        InventoryItemRelation.objects.create(
            item=item,
            inventory=inventory2,
            case_count=3,
            item_count=15,
        )

        results = inventory2.get_previous_difference()
        self.assertEqual(results.count(), 1)
        self.assertEqual(results[0].current_case_count, 3)
        self.assertEqual(results[0].previous_case_count, 2)
        self.assertEqual(results[0].current_item_count, 15)
        self.assertEqual(results[0].previous_item_count, 10)
