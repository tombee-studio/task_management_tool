from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Project, Status, Task
from .dsl import parse_dsl, execute_dsl


class TaskAppModelsTest(TestCase):
    def test_project_string_representation(self):
        project = Project.objects.create(name="Test Project")
        self.assertEqual(str(project), "Test Project")

    def test_task_parent_relationship(self):
        user = get_user_model().objects.create_user(username="user", password="pass")
        status = Status.objects.create(name="Open")
        project = Project.objects.create(name="Test Project")
        parent_task = Task.objects.create(
            title="Parent Task",
            project=project,
            assignee=user,
            status=status,
        )
        child_task = Task.objects.create(
            title="Child Task",
            project=project,
            assignee=user,
            status=status,
            parent=parent_task,
        )
        self.assertEqual(child_task.parent, parent_task)


class DSLTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="user", password="pass")
        self.status = Status.objects.create(name="Open")
        self.project = Project.objects.create(name="Proj")
        # create two tasks with known PKs
        self.src = Task.objects.create(
            title="Src",
            project=self.project,
            assignee=self.user,
            status=self.status,
        )
        self.dst = Task.objects.create(
            title="Dst",
            project=self.project,
            assignee=self.user,
            status=self.status,
        )

    def test_parse_dsl(self):
        text = "LINK %d -> %d" % (self.src.id, self.dst.id)
        ast = parse_dsl(text)
        self.assertEqual(len(ast), 1)
        self.assertEqual(ast[0][0], "link")
        self.assertEqual(ast[0][1], self.src.id)
        self.assertEqual(ast[0][2], self.dst.id)

    def test_execute_dsl_creates_relation(self):
        text = "LINK %d -> %d" % (self.src.id, self.dst.id)
        # ensure no relation initially
        self.assertFalse(self.dst in self.src.related_tasks.all())
        execute_dsl(text)
        # reload from DB
        self.src.refresh_from_db()
        self.assertTrue(self.dst in self.src.related_tasks.all())
