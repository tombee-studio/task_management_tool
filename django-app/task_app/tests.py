from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Project, Status, Task


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
