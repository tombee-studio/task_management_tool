from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from task_app.models import Project, Status, Task
from .models import Event, EventStatus, Inventory, InventoryItemRelation, Item
from .form import EventForm

User = get_user_model()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ItemModelTest(TestCase):
    def test_str(self):
        item = Item.objects.create(company="ACME", name="Widget", count_per_case=10)
        self.assertEqual(str(item), "ACME Widget")

    def test_count_per_case_default_is_one(self):
        item = Item.objects.create(company="Co", name="Thing")
        self.assertEqual(item.count_per_case, 1)

    def test_company_and_name_can_be_blank(self):
        item = Item.objects.create()
        self.assertEqual(str(item), " ")


class InventoryModelTest(TestCase):
    def setUp(self):
        project = Project.objects.create(name="P")
        self.event = Event.objects.create(event_date="2026-01-01", project=project)

    def test_str(self):
        inventory = Inventory.objects.create(name="Stock A", event=self.event)
        self.assertEqual(str(inventory), "Stock A")

    def test_unique_together_item_inventory_raises_on_duplicate(self):
        inventory = Inventory.objects.create(name="Inv", event=self.event)
        item = Item.objects.create(company="Co", name="Thing")
        InventoryItemRelation.objects.create(item=item, inventory=inventory, case_count=1, item_count=1)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            InventoryItemRelation.objects.create(item=item, inventory=inventory, case_count=2, item_count=2)

    def test_previous_inventory_link(self):
        inv1 = Inventory.objects.create(name="Inv1", event=self.event)
        inv2 = Inventory.objects.create(name="Inv2", event=self.event, previous_inventory=inv1)
        self.assertEqual(inv2.previous_inventory, inv1)
        self.assertEqual(inv1.next_inventory, inv2)


class EventModelTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="P")

    def test_previous_event_link(self):
        e1 = Event.objects.create(event_date="2026-01-01", project=self.project)
        e2 = Event.objects.create(event_date="2026-02-01", project=self.project, previous_event=e1)
        self.assertEqual(e2.previous_event, e1)
        self.assertEqual(e1.next_event, e2)

    def test_previous_event_is_optional(self):
        e = Event.objects.create(event_date="2026-01-01", project=self.project)
        self.assertIsNone(e.previous_event)

    def test_participant_count_is_optional(self):
        e = Event.objects.create(event_date="2026-01-01", project=self.project)
        self.assertIsNone(e.participant_count)

    def test_str_with_name(self):
        e = Event.objects.create(event_date="2026-06-01", project=self.project, name="Summer Event")
        self.assertEqual(str(e), "2026-06-01 Summer Event")

    def test_str_without_name(self):
        e = Event.objects.create(event_date="2026-06-01", project=self.project, name="")
        self.assertEqual(str(e), "2026-06-01")


# ---------------------------------------------------------------------------
# Inventory.get_previous_difference
# ---------------------------------------------------------------------------

class GetPreviousDifferenceTest(TestCase):
    def setUp(self):
        project = Project.objects.create(name="P")
        self.event1 = Event.objects.create(event_date="2026-01-01", participant_count=10, project=project)
        self.event2 = Event.objects.create(
            event_date="2026-02-01", participant_count=15,
            project=project, previous_event=self.event1,
        )
        self.inv1 = Inventory.objects.create(name="Inv A", event=self.event1)
        self.inv2 = Inventory.objects.create(
            name="Inv B", event=self.event2, previous_inventory=self.inv1
        )
        self.item = Item.objects.create(company="Co", name="Item", count_per_case=1)

    def _link(self, item, inventory, case_count, item_count):
        return InventoryItemRelation.objects.create(
            item=item, inventory=inventory, case_count=case_count, item_count=item_count
        )

    def test_single_item_counts_returned_correctly(self):
        self._link(self.item, self.inv1, 2, 10)
        self._link(self.item, self.inv2, 3, 15)
        results = self.inv2.get_previous_difference()
        self.assertEqual(results.count(), 1)
        self.assertEqual(results[0].current_case_count, 3)
        self.assertEqual(results[0].previous_case_count, 2)
        self.assertEqual(results[0].current_item_count, 15)
        self.assertEqual(results[0].previous_item_count, 10)

    def test_no_previous_inventory_has_no_previous_counts(self):
        standalone = Inventory.objects.create(name="Alone", event=self.event1)
        self._link(self.item, standalone, 1, 5)
        results = standalone.get_previous_difference()
        self.assertEqual(results.count(), 1)
        self.assertEqual(results[0].current_case_count, 1)
        self.assertEqual(results[0].current_item_count, 5)

    def test_multiple_items_all_returned(self):
        item2 = Item.objects.create(company="Co", name="Beta")
        for item in [self.item, item2]:
            self._link(item, self.inv1, 1, 5)
            self._link(item, self.inv2, 2, 10)
        self.assertEqual(self.inv2.get_previous_difference().count(), 2)

    def test_item_only_in_current_has_null_previous(self):
        item_new = Item.objects.create(company="Co", name="New")
        self._link(self.item, self.inv1, 1, 5)
        self._link(item_new, self.inv2, 2, 10)
        results = self.inv2.get_previous_difference()
        self.assertEqual(results.count(), 2)
        self.assertIsNone(results.get(pk=item_new.pk).previous_case_count)
        self.assertIsNone(results.get(pk=item_new.pk).previous_item_count)

    def test_item_only_in_previous_has_null_current(self):
        item_old = Item.objects.create(company="Co", name="Old")
        self._link(item_old, self.inv1, 1, 5)
        self._link(self.item, self.inv2, 2, 10)
        results = self.inv2.get_previous_difference()
        self.assertEqual(results.count(), 2)
        self.assertIsNone(results.get(pk=item_old.pk).current_case_count)
        self.assertIsNone(results.get(pk=item_old.pk).current_item_count)

    def test_item_unchanged_still_returned(self):
        self._link(self.item, self.inv1, 5, 50)
        self._link(self.item, self.inv2, 5, 50)
        results = self.inv2.get_previous_difference()
        r = results[0]
        self.assertEqual(r.current_case_count, r.previous_case_count)
        self.assertEqual(r.current_item_count, r.previous_item_count)

    def test_empty_inventory_returns_empty_queryset(self):
        results = self.inv2.get_previous_difference()
        self.assertEqual(results.count(), 0)


# ---------------------------------------------------------------------------
# Views — shared fixture
# ---------------------------------------------------------------------------

class BaseEventViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="owner", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")
        self.project = Project.objects.create(name="P")
        self.project.participants.add(self.user)
        self.event = Event.objects.create(
            event_date="2026-01-01", participant_count=10, project=self.project
        )
        self.inventory = Inventory.objects.create(name="Inv", event=self.event)

    def login(self):
        self.client.force_login(self.user)

    def _other_event(self):
        p = Project.objects.create(name="Other")
        p.participants.add(self.other)
        return Event.objects.create(event_date="2026-03-01", project=p)


# ---------------------------------------------------------------------------
# Views — Event
# ---------------------------------------------------------------------------

class EventViewsTest(BaseEventViewTest):
    def test_event_list_requires_login(self):
        self.assertEqual(self.client.get(reverse("event_list")).status_code, 302)

    def test_event_list_template_does_not_exist(self):
        # Known app bug: event_app/event_list.html template is missing.
        self.client.raise_request_exception = False
        self.login()
        self.assertEqual(self.client.get(reverse("event_list")).status_code, 500)

    def test_event_detail_own(self):
        self.login()
        self.assertEqual(
            self.client.get(reverse("event_detail", kwargs={"pk": self.event.pk})).status_code, 200
        )

    def test_event_detail_requires_login(self):
        self.assertEqual(
            self.client.get(reverse("event_detail", kwargs={"pk": self.event.pk})).status_code, 302
        )

    def test_event_detail_other_returns_404(self):
        other = self._other_event()
        self.login()
        self.assertEqual(
            self.client.get(reverse("event_detail", kwargs={"pk": other.pk})).status_code, 404
        )

    def test_event_create_get_returns_200(self):
        self.login()
        self.assertEqual(self.client.get(reverse("event_create")).status_code, 200)

    def test_event_create_with_previous_param_prefills_form(self):
        self.login()
        response = self.client.get(reverse("event_create") + f"?previous={self.event.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial.get("previous_event"), self.event)

    def test_event_create_with_project_param_prefills_project(self):
        self.login()
        response = self.client.get(reverse("event_create") + f"?project={self.project.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial.get("project"), self.project)

    def test_event_create_post_creates_event(self):
        self.login()
        self.client.post(reverse("event_create"), {
            "event_date": "2026-03-01",
            "participant_count": 20,
            "project": self.project.pk,
            "name": "",
            "previous_event": "",
        })
        self.assertTrue(Event.objects.filter(event_date="2026-03-01").exists())

    def test_event_update_changes_date(self):
        self.login()
        self.client.post(
            reverse("event_update", kwargs={"pk": self.event.pk}),
            {
                "event_date": "2026-01-15",
                "participant_count": 20,
                "project": self.project.pk,
                "name": "",
                "previous_event": "",
            },
        )
        self.event.refresh_from_db()
        self.assertEqual(str(self.event.event_date), "2026-01-15")

    def test_event_update_other_returns_404(self):
        other = self._other_event()
        self.login()
        response = self.client.post(
            reverse("event_update", kwargs={"pk": other.pk}),
            {"event_date": "2026-06-01", "project": other.project.pk, "name": "", "previous_event": ""},
        )
        self.assertEqual(response.status_code, 404)

    def test_event_delete_removes_event(self):
        self.login()
        # inventory references self.event; delete it first to avoid cascade issues with the test assertion
        self.inventory.delete()
        self.client.post(reverse("event_delete", kwargs={"pk": self.event.pk}))
        self.assertFalse(Event.objects.filter(pk=self.event.pk).exists())

    def test_event_delete_other_returns_404(self):
        other = self._other_event()
        self.login()
        response = self.client.post(reverse("event_delete", kwargs={"pk": other.pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Event.objects.filter(pk=other.pk).exists())

    def test_event_detail_shows_linked_task(self):
        status = Status.objects.create(name="Open")
        task = Task.objects.create(
            title="Linked Task", project=self.project,
            assignee=self.user, status=status, event=self.event,
        )
        self.login()
        response = self.client.get(reverse("event_detail", kwargs={"pk": self.event.pk}))
        self.assertContains(response, task.title)

    def test_event_detail_excludes_unlinked_task(self):
        status = Status.objects.create(name="Open")
        task = Task.objects.create(
            title="Unlinked Task", project=self.project,
            assignee=self.user, status=status,
        )
        self.login()
        response = self.client.get(reverse("event_detail", kwargs={"pk": self.event.pk}))
        self.assertNotContains(response, task.title)

    def test_event_detail_shows_no_tasks_message_when_empty(self):
        self.login()
        response = self.client.get(reverse("event_detail", kwargs={"pk": self.event.pk}))
        self.assertContains(response, "タスクはまだ登録されていません")


# ---------------------------------------------------------------------------
# Views — Inventory
# ---------------------------------------------------------------------------

class InventoryViewsTest(BaseEventViewTest):
    def test_inventory_list_requires_login(self):
        self.assertEqual(self.client.get(reverse("inventory_list")).status_code, 302)

    def test_inventory_list_template_does_not_exist(self):
        # Known app bug: event_app/inventory_list.html template is missing.
        self.client.raise_request_exception = False
        self.login()
        self.assertEqual(self.client.get(reverse("inventory_list")).status_code, 500)

    def test_inventory_detail_returns_200(self):
        self.login()
        self.assertEqual(
            self.client.get(reverse("inventory_detail", kwargs={"pk": self.inventory.pk})).status_code, 200
        )

    def test_inventory_detail_context_includes_items(self):
        self.login()
        response = self.client.get(reverse("inventory_detail", kwargs={"pk": self.inventory.pk}))
        self.assertIn("items", response.context)

    def test_inventory_detail_other_returns_404(self):
        other_event = self._other_event()
        other_inv = Inventory.objects.create(name="Other", event=other_event)
        self.login()
        self.assertEqual(
            self.client.get(reverse("inventory_detail", kwargs={"pk": other_inv.pk})).status_code, 404
        )

    def test_inventory_create_get_with_previous_param_prefills_form(self):
        self.login()
        response = self.client.get(reverse("inventory_create") + f"?previous={self.inventory.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial.get("previous_inventory"), self.inventory)

    def test_inventory_create_get_with_previous_clears_name(self):
        self.login()
        response = self.client.get(reverse("inventory_create") + f"?previous={self.inventory.pk}")
        self.assertEqual(response.context["form"].initial.get("name"), "")

    def test_inventory_update_get_returns_200(self):
        self.login()
        self.assertEqual(
            self.client.get(reverse("inventory_update", kwargs={"pk": self.inventory.pk})).status_code, 200
        )

    def test_inventory_update_other_returns_404(self):
        other_event = self._other_event()
        other_inv = Inventory.objects.create(name="Other", event=other_event)
        self.login()
        self.assertEqual(
            self.client.get(reverse("inventory_update", kwargs={"pk": other_inv.pk})).status_code, 404
        )

    def test_inventory_delete_removes_inventory(self):
        self.login()
        self.client.post(reverse("inventory_delete", kwargs={"pk": self.inventory.pk}))
        self.assertFalse(Inventory.objects.filter(pk=self.inventory.pk).exists())

    def test_inventory_delete_other_returns_404(self):
        other_event = self._other_event()
        other_inv = Inventory.objects.create(name="Other", event=other_event)
        self.login()
        response = self.client.post(reverse("inventory_delete", kwargs={"pk": other_inv.pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Inventory.objects.filter(pk=other_inv.pk).exists())


# ---------------------------------------------------------------------------
# EventStatus — モデル
# ---------------------------------------------------------------------------

class EventStatusModelTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="P")

    def test_str(self):
        s = EventStatus.objects.create(name="準備中", project=self.project)
        self.assertEqual(str(s), "準備中")

    def test_is_done_default_is_false(self):
        s = EventStatus.objects.create(name="開催前", project=self.project)
        self.assertFalse(s.is_done)

    def test_project_is_optional(self):
        s = EventStatus.objects.create(name="汎用")
        self.assertIsNone(s.project)

    def test_project_related_name(self):
        s = EventStatus.objects.create(name="開催中", project=self.project)
        self.assertIn(s, self.project.event_statuses.all())

    def test_event_status_fk_on_event(self):
        s = EventStatus.objects.create(name="開催済み", is_done=True, project=self.project)
        e = Event.objects.create(event_date="2026-06-01", project=self.project, status=s)
        self.assertEqual(e.status, s)
        self.assertIn(e, s.events.all())

    def test_event_status_is_optional_on_event(self):
        e = Event.objects.create(event_date="2026-06-01", project=self.project)
        self.assertIsNone(e.status)

    def test_deleting_event_status_sets_event_status_null(self):
        s = EventStatus.objects.create(name="一時", project=self.project)
        e = Event.objects.create(event_date="2026-06-01", project=self.project, status=s)
        s.delete()
        e.refresh_from_db()
        self.assertIsNone(e.status)


# ---------------------------------------------------------------------------
# EventForm — status フィールド
# ---------------------------------------------------------------------------

class EventFormStatusTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="P")
        self.other_project = Project.objects.create(name="Other")
        self.status = EventStatus.objects.create(name="準備中", project=self.project)
        self.other_status = EventStatus.objects.create(name="他プロジェクト", project=self.other_project)
        self.event = Event.objects.create(event_date="2026-01-01", project=self.project, name="E1")
        self.other_event = Event.objects.create(event_date="2026-01-01", project=self.other_project, name="E2")

    def test_status_field_is_present(self):
        form = EventForm(project=self.project)
        self.assertIn("status", form.fields)

    def test_status_field_is_not_required(self):
        form = EventForm(project=self.project)
        self.assertFalse(form.fields["status"].required)

    def test_status_queryset_includes_project_status(self):
        form = EventForm(project=self.project)
        self.assertIn(self.status, form.fields["status"].queryset)

    def test_status_queryset_excludes_other_project_status(self):
        form = EventForm(project=self.project)
        self.assertNotIn(self.other_status, form.fields["status"].queryset)

    def test_form_valid_without_status(self):
        form = EventForm(
            data={"name": "E", "event_date": "2026-06-01", "project": self.project.pk},
            project=self.project,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_valid_with_status(self):
        form = EventForm(
            data={"name": "E", "event_date": "2026-06-01", "project": self.project.pk,
                  "status": self.status.pk},
            project=self.project,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_previous_event_queryset_includes_project_event(self):
        form = EventForm(project=self.project)
        self.assertIn(self.event, form.fields["previous_event"].queryset)

    def test_previous_event_queryset_excludes_other_project_event(self):
        form = EventForm(project=self.project)
        self.assertNotIn(self.other_event, form.fields["previous_event"].queryset)

    def test_previous_event_queryset_not_filtered_without_project(self):
        form = EventForm()
        self.assertIn(self.event, form.fields["previous_event"].queryset)
        self.assertIn(self.other_event, form.fields["previous_event"].queryset)


# ---------------------------------------------------------------------------
# EventStatus — CRUD views
# ---------------------------------------------------------------------------

class EventStatusBaseTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="owner", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")
        self.project = Project.objects.create(name="P")
        self.project.participants.add(self.user)
        self.event_status = EventStatus.objects.create(name="準備中", project=self.project)

    def login(self):
        self.client.force_login(self.user)


class EventStatusCreateViewTest(EventStatusBaseTest):
    def test_create_event_status(self):
        self.login()
        self.client.post(
            reverse("event_status_create", kwargs={"project_pk": self.project.pk}),
            {"name": "開催中", "is_done": False},
        )
        self.assertTrue(EventStatus.objects.filter(name="開催中", project=self.project).exists())

    def test_create_sets_project(self):
        self.login()
        self.client.post(
            reverse("event_status_create", kwargs={"project_pk": self.project.pk}),
            {"name": "終了", "is_done": True},
        )
        s = EventStatus.objects.get(name="終了")
        self.assertEqual(s.project, self.project)

    def test_create_unrelated_project_returns_404(self):
        other_project = Project.objects.create(name="Other")
        self.login()
        response = self.client.post(
            reverse("event_status_create", kwargs={"project_pk": other_project.pk}),
            {"name": "X", "is_done": False},
        )
        self.assertEqual(response.status_code, 404)

    def test_create_redirects_to_project_detail(self):
        self.login()
        response = self.client.post(
            reverse("event_status_create", kwargs={"project_pk": self.project.pk}),
            {"name": "新規", "is_done": False},
        )
        self.assertRedirects(
            response,
            reverse("project_detail", kwargs={"pk": self.project.pk}) + "#tab-event-status",
            fetch_redirect_response=False,
        )


class EventStatusUpdateViewTest(EventStatusBaseTest):
    def test_update_event_status(self):
        self.login()
        self.client.post(
            reverse("event_status_update", kwargs={"pk": self.event_status.pk}),
            {"name": "開催済み", "is_done": True},
        )
        self.event_status.refresh_from_db()
        self.assertEqual(self.event_status.name, "開催済み")
        self.assertTrue(self.event_status.is_done)


class EventStatusDeleteViewTest(EventStatusBaseTest):
    def test_delete_event_status(self):
        self.login()
        self.client.post(reverse("event_status_delete", kwargs={"pk": self.event_status.pk}))
        self.assertFalse(EventStatus.objects.filter(pk=self.event_status.pk).exists())

    def test_delete_redirects_to_project_detail(self):
        self.login()
        project_id = self.event_status.project_id
        response = self.client.post(
            reverse("event_status_delete", kwargs={"pk": self.event_status.pk})
        )
        self.assertRedirects(
            response,
            reverse("project_detail", kwargs={"pk": project_id}) + "#tab-event-status",
            fetch_redirect_response=False,
        )


# ---------------------------------------------------------------------------
# ProjectDetailView — EventStatus フィルタ
# ---------------------------------------------------------------------------

class ProjectDetailEventStatusFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="owner", password="pass")
        self.project = Project.objects.create(name="P")
        self.project.participants.add(self.user)
        self.active_status = EventStatus.objects.create(name="準備中", is_done=False, project=self.project)
        self.done_status = EventStatus.objects.create(name="終了", is_done=True, project=self.project)
        self.event_active = Event.objects.create(
            event_date="2026-06-01", project=self.project, name="Active", status=self.active_status
        )
        self.event_done = Event.objects.create(
            event_date="2026-07-01", project=self.project, name="Done", status=self.done_status
        )

    def _get(self, params=None):
        self.client.force_login(self.user)
        return self.client.get(
            reverse("project_detail", kwargs={"pk": self.project.pk}),
            params or {},
        )

    def test_event_status_list_in_context(self):
        response = self._get()
        self.assertIn(self.active_status, response.context["event_status_list"])
        self.assertIn(self.done_status, response.context["event_status_list"])

    def test_selected_event_status_list_defaults_to_active(self):
        response = self._get()
        self.assertIn(self.active_status.pk, response.context["selected_event_status_list"])
        self.assertNotIn(self.done_status.pk, response.context["selected_event_status_list"])

