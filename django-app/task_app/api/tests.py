import json
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from task_app.models import Comment, Project, Rule, Status, Tag, Task, UserPreferences

User = get_user_model()

BASE = '/api/task_app'


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

class BaseAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='pass')
        self.other = User.objects.create_user(username='other', password='pass')
        self.project = Project.objects.create(name='P')
        self.status = Status.objects.create(name='Open', project=self.project)
        self.task = Task.objects.create(
            title='T', project=self.project,
            assignee=self.user, status=self.status,
        )

    def auth(self):
        self.client.force_authenticate(user=self.user)


# ---------------------------------------------------------------------------
# Authentication — all endpoints require a logged-in user
# ---------------------------------------------------------------------------

class AuthenticationTest(BaseAPITest):
    """
    SessionAuthentication returns 403 (not 401) for unauthenticated requests
    because it provides no WWW-Authenticate header.
    """
    endpoints = [
        f'{BASE}/projects/',
        f'{BASE}/statuses/',
        f'{BASE}/comments/',
        f'{BASE}/tags/',
        f'{BASE}/tasks/',
        f'{BASE}/user-preferences/',
        f'{BASE}/rules/',
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
# Project
# ---------------------------------------------------------------------------

class ProjectAPITest(BaseAPITest):
    URL = f'{BASE}/projects/'

    def detail(self, pk=None):
        return f'{self.URL}{pk or self.project.pk}/'

    def test_list_returns_200(self):
        self.auth()
        self.assertEqual(self.client.get(self.URL).status_code, status.HTTP_200_OK)

    def test_list_includes_project(self):
        self.auth()
        ids = [p['id'] for p in self.client.get(self.URL).data]
        self.assertIn(self.project.pk, ids)

    def test_create_returns_201(self):
        self.auth()
        r = self.client.post(self.URL, {'name': 'New'})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_create_persists(self):
        self.auth()
        self.client.post(self.URL, {'name': 'New'})
        self.assertTrue(Project.objects.filter(name='New').exists())

    def test_create_sets_fields(self):
        self.auth()
        r = self.client.post(self.URL, {'name': 'G', 'git_url': 'https://github.com/x/y'})
        self.assertEqual(r.data['git_url'], 'https://github.com/x/y')

    def test_retrieve_returns_200(self):
        self.auth()
        self.assertEqual(self.client.get(self.detail()).status_code, status.HTTP_200_OK)

    def test_retrieve_correct_name(self):
        self.auth()
        self.assertEqual(self.client.get(self.detail()).data['name'], 'P')

    def test_update_returns_200(self):
        self.auth()
        r = self.client.patch(self.detail(), {'name': 'Updated'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_update_persists(self):
        self.auth()
        self.client.patch(self.detail(), {'name': 'Updated'})
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'Updated')

    def test_delete_returns_204(self):
        self.auth()
        p = Project.objects.create(name='Del')
        self.assertEqual(self.client.delete(self.detail(p.pk)).status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_removes_object(self):
        self.auth()
        p = Project.objects.create(name='Del')
        self.client.delete(self.detail(p.pk))
        self.assertFalse(Project.objects.filter(pk=p.pk).exists())

    def test_response_contains_timestamps(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)

    def test_participants_not_in_response(self):
        self.auth()
        self.assertNotIn('participants', self.client.get(self.detail()).data)

    def test_created_at_is_read_only(self):
        self.auth()
        r = self.client.post(self.URL, {'name': 'X', 'created_at': '2000-01-01T00:00:00Z'})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(r.data['created_at'], '2000-01-01T00:00:00Z')


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

class StatusAPITest(BaseAPITest):
    URL = f'{BASE}/statuses/'

    def detail(self, pk=None):
        return f'{self.URL}{pk or self.status.pk}/'

    def test_list_returns_200(self):
        self.auth()
        self.assertEqual(self.client.get(self.URL).status_code, status.HTTP_200_OK)

    def test_create_returns_201(self):
        self.auth()
        r = self.client.post(self.URL, {'name': 'Done', 'is_done': True, 'project': self.project.pk})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_create_persists(self):
        self.auth()
        self.client.post(self.URL, {'name': 'Done', 'is_done': True, 'project': self.project.pk})
        self.assertTrue(Status.objects.filter(name='Done').exists())

    def test_retrieve_returns_correct_data(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertEqual(data['name'], 'Open')
        self.assertFalse(data['is_done'])
        self.assertEqual(data['project'], self.project.pk)

    def test_update_is_done(self):
        self.auth()
        self.client.patch(self.detail(), {'is_done': True})
        self.status.refresh_from_db()
        self.assertTrue(self.status.is_done)

    def test_delete_removes_object(self):
        self.auth()
        s = Status.objects.create(name='Temp', project=self.project)
        self.client.delete(f'{self.URL}{s.pk}/')
        self.assertFalse(Status.objects.filter(pk=s.pk).exists())

    def test_response_contains_timestamps(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)


# ---------------------------------------------------------------------------
# Comment
# ---------------------------------------------------------------------------

class CommentAPITest(BaseAPITest):
    URL = f'{BASE}/comments/'

    def setUp(self):
        super().setUp()
        self.comment = Comment.objects.create(
            author=self.user, task=self.task, description='Hello'
        )

    def detail(self, pk=None):
        return f'{self.URL}{pk or self.comment.pk}/'

    def test_list_returns_200(self):
        self.auth()
        self.assertEqual(self.client.get(self.URL).status_code, status.HTTP_200_OK)

    def test_create_returns_201(self):
        self.auth()
        r = self.client.post(self.URL, {
            'author': self.user.pk, 'task': self.task.pk, 'description': 'New',
        })
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_create_persists(self):
        self.auth()
        self.client.post(self.URL, {
            'author': self.user.pk, 'task': self.task.pk, 'description': 'New',
        })
        self.assertTrue(Comment.objects.filter(description='New').exists())

    def test_retrieve_correct_description(self):
        self.auth()
        self.assertEqual(self.client.get(self.detail()).data['description'], 'Hello')

    def test_update_description(self):
        self.auth()
        self.client.patch(self.detail(), {'description': 'Updated'})
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.description, 'Updated')

    def test_delete_removes_object(self):
        self.auth()
        self.client.delete(self.detail())
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_response_contains_timestamps(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)


# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------

class TagAPITest(BaseAPITest):
    URL = f'{BASE}/tags/'

    def setUp(self):
        super().setUp()
        self.tag = Tag.objects.create(name='urgent')

    def detail(self, pk=None):
        return f'{self.URL}{pk or self.tag.pk}/'

    def test_list_returns_200(self):
        self.auth()
        self.assertEqual(self.client.get(self.URL).status_code, status.HTTP_200_OK)

    def test_create_returns_201(self):
        self.auth()
        r = self.client.post(self.URL, {'name': 'bug'})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_create_persists(self):
        self.auth()
        self.client.post(self.URL, {'name': 'bug'})
        self.assertTrue(Tag.objects.filter(name='bug').exists())

    def test_retrieve_correct_name(self):
        self.auth()
        self.assertEqual(self.client.get(self.detail()).data['name'], 'urgent')

    def test_update_name(self):
        self.auth()
        self.client.patch(self.detail(), {'name': 'critical'})
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.name, 'critical')

    def test_delete_removes_object(self):
        self.auth()
        self.client.delete(self.detail())
        self.assertFalse(Tag.objects.filter(pk=self.tag.pk).exists())

    def test_no_m2m_tasks_in_response(self):
        self.auth()
        self.assertNotIn('tasks', self.client.get(self.detail()).data)


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

class TaskAPITest(BaseAPITest):
    URL = f'{BASE}/tasks/'

    def detail(self, pk=None):
        return f'{self.URL}{pk or self.task.pk}/'

    def _payload(self, **kwargs):
        data = {
            'title': 'New Task',
            'project': self.project.pk,
            'assignee': self.user.pk,
            'status': self.status.pk,
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
        self.assertTrue(Task.objects.filter(title='New Task').exists())

    def test_create_with_deadline(self):
        self.auth()
        r = self.client.post(self.URL, self._payload(deadline='2026-12-31'))
        self.assertEqual(r.data['deadline'], '2026-12-31')

    def test_create_with_parent(self):
        self.auth()
        r = self.client.post(self.URL, self._payload(parent=self.task.pk))
        self.assertEqual(r.data['parent'], self.task.pk)

    def test_retrieve_returns_200(self):
        self.auth()
        self.assertEqual(self.client.get(self.detail()).status_code, status.HTTP_200_OK)

    def test_retrieve_correct_title(self):
        self.auth()
        self.assertEqual(self.client.get(self.detail()).data['title'], 'T')

    def test_update_title(self):
        self.auth()
        self.client.patch(self.detail(), {'title': 'Updated'})
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Updated')

    def test_update_status(self):
        done = Status.objects.create(name='Done', is_done=True, project=self.project)
        self.auth()
        self.client.patch(self.detail(), {'status': done.pk})
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, done)

    def test_delete_returns_204(self):
        self.auth()
        t = Task.objects.create(
            title='Del', project=self.project, assignee=self.user, status=self.status
        )
        self.assertEqual(self.client.delete(self.detail(t.pk)).status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_removes_object(self):
        self.auth()
        t = Task.objects.create(
            title='Del', project=self.project, assignee=self.user, status=self.status
        )
        self.client.delete(self.detail(t.pk))
        self.assertFalse(Task.objects.filter(pk=t.pk).exists())

    def test_response_contains_timestamps(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)

    def test_m2m_fields_not_in_response(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertNotIn('related_tasks', data)
        self.assertNotIn('watched', data)
        self.assertNotIn('tags', data)

    def test_created_at_is_read_only(self):
        self.auth()
        r = self.client.post(self.URL, self._payload(created_at='2000-01-01T00:00:00Z'))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(r.data['created_at'], '2000-01-01T00:00:00Z')


# ---------------------------------------------------------------------------
# UserPreferences
# ---------------------------------------------------------------------------

class UserPreferencesAPITest(BaseAPITest):
    URL = f'{BASE}/user-preferences/'

    def setUp(self):
        super().setUp()
        # create_user_preferences signal auto-creates one per user
        self.prefs = UserPreferences.objects.get(user=self.user)
        self.prefs.config = '{}'
        self.prefs.save()

    def detail(self, pk=None):
        return f'{self.URL}{pk or self.prefs.pk}/'

    def test_list_returns_200(self):
        self.auth()
        self.assertEqual(self.client.get(self.URL).status_code, status.HTTP_200_OK)

    def test_create_returns_201(self):
        # Delete auto-created preferences for other, then re-create via API
        self.auth()
        UserPreferences.objects.filter(user=self.other).delete()
        r = self.client.post(self.URL, {'user': self.other.pk, 'config': '{}'})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_create_persists(self):
        self.auth()
        UserPreferences.objects.filter(user=self.other).delete()
        self.client.post(self.URL, {'user': self.other.pk, 'config': '{}'})
        self.assertTrue(UserPreferences.objects.filter(user=self.other).exists())

    def test_retrieve_correct_config(self):
        self.auth()
        self.assertEqual(self.client.get(self.detail()).data['config'], '{}')

    def test_update_config(self):
        self.auth()
        self.client.patch(self.detail(), {'config': '{"theme":"dark"}'})
        self.prefs.refresh_from_db()
        self.assertEqual(self.prefs.config, '{"theme":"dark"}')

    def test_delete_removes_object(self):
        self.auth()
        other_prefs = UserPreferences.objects.get(user=self.other)
        self.client.delete(f'{self.URL}{other_prefs.pk}/')
        self.assertFalse(UserPreferences.objects.filter(pk=other_prefs.pk).exists())


# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------

class RuleAPITest(BaseAPITest):
    URL = f'{BASE}/rules/'

    def setUp(self):
        super().setUp()
        self.rule = Rule.objects.create(
            project=self.project, name='R',
            pattern=r'relates to (\d+)', dsl_template='LINK {task_id} -> {group1}',
        )

    def detail(self, pk=None):
        return f'{self.URL}{pk or self.rule.pk}/'

    def _payload(self, **kwargs):
        data = {
            'project': self.project.pk,
            'name': 'New Rule',
            'pattern': r'\d+',
            'dsl_template': 'LINK {task_id} -> {group1}',
            'enabled': True,
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
        self.assertTrue(Rule.objects.filter(name='New Rule').exists())

    def test_retrieve_correct_data(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertEqual(data['name'], 'R')
        self.assertEqual(data['project'], self.project.pk)
        self.assertTrue(data['enabled'])

    def test_update_enabled(self):
        self.auth()
        self.client.patch(self.detail(), {'enabled': False})
        self.rule.refresh_from_db()
        self.assertFalse(self.rule.enabled)

    def test_update_pattern(self):
        self.auth()
        self.client.patch(self.detail(), {'pattern': r'new pattern'})
        self.rule.refresh_from_db()
        self.assertEqual(self.rule.pattern, 'new pattern')

    def test_delete_removes_object(self):
        self.auth()
        self.client.delete(self.detail())
        self.assertFalse(Rule.objects.filter(pk=self.rule.pk).exists())

    def test_response_contains_timestamps(self):
        self.auth()
        data = self.client.get(self.detail()).data
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
