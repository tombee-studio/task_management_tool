from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .agent_help import (
    AGENT_SCRIPT_GLOBALS, AGENT_CTX_METHODS, AGENT_SCRIPT_SAMPLES, get_agent_help,
)
from .models import Project

User = get_user_model()


# ---------------------------------------------------------------------------
# 構造化データ（API 定義・サンプル）
# ---------------------------------------------------------------------------

class AgentHelpDataTest(TestCase):
    def test_globals_not_empty(self):
        self.assertTrue(AGENT_SCRIPT_GLOBALS)

    def test_global_entries_have_required_keys(self):
        for g in AGENT_SCRIPT_GLOBALS:
            self.assertIn('name', g)
            self.assertIn('type', g)
            self.assertIn('description', g)

    def test_methods_not_empty(self):
        self.assertTrue(AGENT_CTX_METHODS)

    def test_method_entries_have_required_keys(self):
        for m in AGENT_CTX_METHODS:
            self.assertIn('name', m)
            self.assertIn('signature', m)
            self.assertIn('returns', m)
            self.assertIn('description', m)

    def test_methods_cover_core_api(self):
        names = {m['name'] for m in AGENT_CTX_METHODS}
        for expected in (
            'clone_git_url', 'get_task', 'get_kinds', 'decide_strategy',
            'branch', 'push', 'gh_create_pr', 'run_agent', 'change_assignee',
        ):
            self.assertIn(expected, names)

    def test_samples_not_empty(self):
        self.assertTrue(AGENT_SCRIPT_SAMPLES)

    def test_sample_entries_have_required_keys(self):
        for s in AGENT_SCRIPT_SAMPLES:
            self.assertIn('title', s)
            self.assertIn('description', s)
            self.assertIn('code', s)

    def test_sample_code_is_non_empty(self):
        for s in AGENT_SCRIPT_SAMPLES:
            self.assertTrue(s['code'].strip())

    def test_get_agent_help_structure(self):
        help_data = get_agent_help()
        self.assertIn('globals', help_data)
        self.assertIn('methods', help_data)
        self.assertIn('samples', help_data)
        self.assertEqual(help_data['methods'], AGENT_CTX_METHODS)


# ---------------------------------------------------------------------------
# プロジェクト編集ページのコンテキスト
# ---------------------------------------------------------------------------

class ProjectUpdateAgentHelpContextTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='owner', password='pass')
        self.project = Project.objects.create(name='P')
        self.project.participants.add(self.user)

    def test_update_view_context_contains_agent_help(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('project_update', kwargs={'pk': self.project.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn('agent_globals', response.context)
        self.assertIn('agent_methods', response.context)
        self.assertIn('agent_samples', response.context)

    def test_update_view_agent_methods_match_source(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('project_update', kwargs={'pk': self.project.pk}))
        self.assertEqual(list(response.context['agent_methods']), AGENT_CTX_METHODS)
