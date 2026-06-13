from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from task_app.models import Project
from event_app.models import Event, EventStatus, Inventory, InventoryItemRelation, Item

User = get_user_model()

BASE = '/api/event_app'


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

class BaseEventAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='pass')
        self.other = User.objects.create_user(username='other', password='pass')
        self.project = Project.objects.create(name='P')
        self.event_status = EventStatus.objects.create(name='準備中', project=self.project)
        self.event = Event.objects.create(
            name='Ev', event_date='2026-06-01',
            project=self.project, status=self.event_status,
        )
        self.inventory = Inventory.objects.create(name='Inv', event=self.event)
        self.item = Item.objects.create(company='Co', name='Widget', count_per_case=10)

    def auth(self):
        self.client.force_authenticate(user=self.user)


# ---------------------------------------------------------------------------
# Authentication — all endpoints require a logged-in user
# ---------------------------------------------------------------------------

class AuthenticationTest(BaseEventAPITest):
    """
    SessionAuthentication returns 403 (not 401) for unauthenticated requests
    because it provides no WWW-Authenticate header.
    """
    endpoints = [
        f'{BASE}/event-statuses/',
        f'{BASE}/events/',
        f'{BASE}/inventories/',
        f'{BASE}/items/',
        f'{BASE}/inventory-item-relations/',
    ]

    def test_unauthenticated_list_is_denied(self):
        for url in self.endpoints:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_post_is_denied(self):
        for url in self.endpoints:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, {}).status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# EventStatus
# ---------------------------------------------------------------------------

class EventStatusAPITest(BaseEventAPITest):
    URL = f'{BASE}/event-statuses/'

    def detail(self, pk=None):
        return f'{self.URL}{pk or self.event_status.pk}/'

    def test_list_returns_200(self):
        self.auth()
        self.assertEqual(self.client.get(self.URL).status_code, status.HTTP_200_OK)

    def test_list_includes_event_status(self):
        self.auth()
        ids = [s['id'] for s in self.client.get(self.URL).data]
        self.assertIn(self.event_status.pk, ids)

    def test_create_returns_201(self):
        self.auth()
        r = self.client.post(self.URL, {'name': '開催中', 'is_done': False, 'project': self.project.pk})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_create_persists(self):
        self.auth()
        self.client.post(self.URL, {'name': '開催中', 'is_done': False, 'project': self.project.pk})
        self.assertTrue(EventStatus.objects.filter(name='開催中').exists())

    def test_create_without_project_is_allowed(self):
        self.auth()
        r = self.client.post(self.URL, {'name': '汎用', 'is_done': False})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(r.data['project'])

    def test_retrieve_returns_200(self):
        self.auth()
        self.assertEqual(self.client.get(self.detail()).status_code, status.HTTP_200_OK)

    def test_retrieve_correct_data(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertEqual(data['name'], '準備中')
        self.assertFalse(data['is_done'])
        self.assertEqual(data['project'], self.project.pk)

    def test_update_is_done(self):
        self.auth()
        self.client.patch(self.detail(), {'is_done': True})
        self.event_status.refresh_from_db()
        self.assertTrue(self.event_status.is_done)

    def test_update_name(self):
        self.auth()
        self.client.patch(self.detail(), {'name': '開催済み'})
        self.event_status.refresh_from_db()
        self.assertEqual(self.event_status.name, '開催済み')

    def test_delete_returns_204(self):
        self.auth()
        s = EventStatus.objects.create(name='Temp', project=self.project)
        self.assertEqual(self.client.delete(f'{self.URL}{s.pk}/').status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_removes_object(self):
        self.auth()
        s = EventStatus.objects.create(name='Temp', project=self.project)
        self.client.delete(f'{self.URL}{s.pk}/')
        self.assertFalse(EventStatus.objects.filter(pk=s.pk).exists())

    def test_response_contains_timestamps(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)

    def test_created_at_is_read_only(self):
        self.auth()
        r = self.client.post(self.URL, {
            'name': 'X', 'is_done': False, 'created_at': '2000-01-01T00:00:00Z'
        })
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(r.data['created_at'], '2000-01-01T00:00:00Z')


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

class EventAPITest(BaseEventAPITest):
    URL = f'{BASE}/events/'

    def detail(self, pk=None):
        return f'{self.URL}{pk or self.event.pk}/'

    def _payload(self, **kwargs):
        data = {
            'name': 'New Event',
            'event_date': '2026-07-01',
            'project': self.project.pk,
        }
        data.update(kwargs)
        return data

    def test_list_returns_200(self):
        self.auth()
        self.assertEqual(self.client.get(self.URL).status_code, status.HTTP_200_OK)

    def test_create_returns_201(self):
        self.auth()
        r = self.client.post(self.URL, self._payload())
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_create_persists(self):
        self.auth()
        self.client.post(self.URL, self._payload())
        self.assertTrue(Event.objects.filter(name='New Event').exists())

    def test_create_with_status(self):
        self.auth()
        r = self.client.post(self.URL, self._payload(status=self.event_status.pk))
        self.assertEqual(r.data['status'], self.event_status.pk)

    def test_create_with_participant_count(self):
        self.auth()
        r = self.client.post(self.URL, self._payload(participant_count=50))
        self.assertEqual(r.data['participant_count'], 50)

    def test_create_with_previous_event(self):
        self.auth()
        r = self.client.post(self.URL, self._payload(previous_event=self.event.pk))
        self.assertEqual(r.data['previous_event'], self.event.pk)

    def test_retrieve_returns_200(self):
        self.auth()
        self.assertEqual(self.client.get(self.detail()).status_code, status.HTTP_200_OK)

    def test_retrieve_correct_data(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertEqual(data['name'], 'Ev')
        self.assertEqual(data['event_date'], '2026-06-01')
        self.assertEqual(data['project'], self.project.pk)

    def test_update_name(self):
        self.auth()
        self.client.patch(self.detail(), {'name': 'Updated'})
        self.event.refresh_from_db()
        self.assertEqual(self.event.name, 'Updated')

    def test_update_participant_count(self):
        self.auth()
        self.client.patch(self.detail(), {'participant_count': 100})
        self.event.refresh_from_db()
        self.assertEqual(self.event.participant_count, 100)

    def test_delete_returns_204(self):
        self.auth()
        e = Event.objects.create(event_date='2026-09-01', project=self.project)
        self.assertEqual(self.client.delete(f'{self.URL}{e.pk}/').status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_removes_object(self):
        self.auth()
        e = Event.objects.create(event_date='2026-09-01', project=self.project)
        self.client.delete(f'{self.URL}{e.pk}/')
        self.assertFalse(Event.objects.filter(pk=e.pk).exists())

    def test_response_contains_timestamps(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)

    def test_created_at_is_read_only(self):
        self.auth()
        r = self.client.post(self.URL, self._payload(created_at='2000-01-01T00:00:00Z'))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(r.data['created_at'], '2000-01-01T00:00:00Z')


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

class InventoryAPITest(BaseEventAPITest):
    URL = f'{BASE}/inventories/'

    def detail(self, pk=None):
        return f'{self.URL}{pk or self.inventory.pk}/'

    def test_list_returns_200(self):
        self.auth()
        self.assertEqual(self.client.get(self.URL).status_code, status.HTTP_200_OK)

    def test_create_returns_201(self):
        self.auth()
        r = self.client.post(self.URL, {'name': 'New Inv', 'event': self.event.pk})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_create_persists(self):
        self.auth()
        self.client.post(self.URL, {'name': 'New Inv', 'event': self.event.pk})
        self.assertTrue(Inventory.objects.filter(name='New Inv').exists())

    def test_create_with_previous_inventory(self):
        self.auth()
        r = self.client.post(self.URL, {
            'name': 'Next Inv', 'event': self.event.pk,
            'previous_inventory': self.inventory.pk,
        })
        self.assertEqual(r.data['previous_inventory'], self.inventory.pk)

    def test_retrieve_correct_data(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertEqual(data['name'], 'Inv')
        self.assertEqual(data['event'], self.event.pk)

    def test_update_name(self):
        self.auth()
        self.client.patch(self.detail(), {'name': 'Updated Inv'})
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.name, 'Updated Inv')

    def test_delete_removes_object(self):
        self.auth()
        inv = Inventory.objects.create(name='Del', event=self.event)
        self.client.delete(f'{self.URL}{inv.pk}/')
        self.assertFalse(Inventory.objects.filter(pk=inv.pk).exists())

    def test_m2m_items_not_in_response(self):
        self.auth()
        self.assertNotIn('items', self.client.get(self.detail()).data)

    def test_response_contains_timestamps(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)


# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------

class ItemAPITest(BaseEventAPITest):
    URL = f'{BASE}/items/'

    def detail(self, pk=None):
        return f'{self.URL}{pk or self.item.pk}/'

    def test_list_returns_200(self):
        self.auth()
        self.assertEqual(self.client.get(self.URL).status_code, status.HTTP_200_OK)

    def test_create_returns_201(self):
        self.auth()
        r = self.client.post(self.URL, {'company': 'ACME', 'name': 'Gadget', 'count_per_case': 5})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_create_persists(self):
        self.auth()
        self.client.post(self.URL, {'company': 'ACME', 'name': 'Gadget', 'count_per_case': 5})
        self.assertTrue(Item.objects.filter(name='Gadget').exists())

    def test_retrieve_correct_data(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertEqual(data['company'], 'Co')
        self.assertEqual(data['name'], 'Widget')
        self.assertEqual(data['count_per_case'], 10)

    def test_update_count_per_case(self):
        self.auth()
        self.client.patch(self.detail(), {'count_per_case': 20})
        self.item.refresh_from_db()
        self.assertEqual(self.item.count_per_case, 20)

    def test_update_company(self):
        self.auth()
        self.client.patch(self.detail(), {'company': 'NewCo'})
        self.item.refresh_from_db()
        self.assertEqual(self.item.company, 'NewCo')

    def test_delete_returns_204(self):
        self.auth()
        item = Item.objects.create(company='Del', name='Thing')
        self.assertEqual(self.client.delete(f'{self.URL}{item.pk}/').status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_removes_object(self):
        self.auth()
        item = Item.objects.create(company='Del', name='Thing')
        self.client.delete(f'{self.URL}{item.pk}/')
        self.assertFalse(Item.objects.filter(pk=item.pk).exists())

    def test_response_contains_timestamps(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)

    def test_created_at_is_read_only(self):
        self.auth()
        r = self.client.post(self.URL, {
            'company': 'X', 'name': 'Y', 'created_at': '2000-01-01T00:00:00Z'
        })
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(r.data['created_at'], '2000-01-01T00:00:00Z')


# ---------------------------------------------------------------------------
# InventoryItemRelation
# ---------------------------------------------------------------------------

class InventoryItemRelationAPITest(BaseEventAPITest):
    URL = f'{BASE}/inventory-item-relations/'

    def setUp(self):
        super().setUp()
        self.relation = InventoryItemRelation.objects.create(
            item=self.item, inventory=self.inventory,
            case_count=5, item_count=50,
        )

    def detail(self, pk=None):
        return f'{self.URL}{pk or self.relation.pk}/'

    def test_list_returns_200(self):
        self.auth()
        self.assertEqual(self.client.get(self.URL).status_code, status.HTTP_200_OK)

    def test_create_returns_201(self):
        self.auth()
        new_item = Item.objects.create(company='NewCo', name='NewThing')
        r = self.client.post(self.URL, {
            'item': new_item.pk, 'inventory': self.inventory.pk,
            'case_count': 3, 'item_count': 30,
        })
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_create_persists(self):
        self.auth()
        new_item = Item.objects.create(company='NewCo', name='NewThing')
        self.client.post(self.URL, {
            'item': new_item.pk, 'inventory': self.inventory.pk,
            'case_count': 3, 'item_count': 30,
        })
        self.assertTrue(
            InventoryItemRelation.objects.filter(item=new_item, inventory=self.inventory).exists()
        )

    def test_retrieve_correct_data(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertEqual(data['item'], self.item.pk)
        self.assertEqual(data['inventory'], self.inventory.pk)
        self.assertEqual(data['case_count'], 5)
        self.assertEqual(data['item_count'], 50)

    def test_update_case_count(self):
        self.auth()
        self.client.patch(self.detail(), {'case_count': 10})
        self.relation.refresh_from_db()
        self.assertEqual(self.relation.case_count, 10)

    def test_update_item_count(self):
        self.auth()
        self.client.patch(self.detail(), {'item_count': 99})
        self.relation.refresh_from_db()
        self.assertEqual(self.relation.item_count, 99)

    def test_delete_returns_204(self):
        self.auth()
        item = Item.objects.create(company='D', name='D')
        rel = InventoryItemRelation.objects.create(item=item, inventory=self.inventory)
        self.assertEqual(self.client.delete(f'{self.URL}{rel.pk}/').status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_removes_object(self):
        self.auth()
        item = Item.objects.create(company='D', name='D')
        rel = InventoryItemRelation.objects.create(item=item, inventory=self.inventory)
        self.client.delete(f'{self.URL}{rel.pk}/')
        self.assertFalse(InventoryItemRelation.objects.filter(pk=rel.pk).exists())

    def test_response_contains_timestamps(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
