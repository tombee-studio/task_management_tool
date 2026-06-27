from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import Client, TestCase
from django.urls import reverse

from .agent_help import get_agent_help
from .models import Project

User = get_user_model()


class AgentHelpDataTest(TestCase):
    def test_get_agent_help_returns_all_sections(self):
        help_data = get_agent_help()
        for key in ("globals", "safe_builtins", "data_classes",
                    "api_reference", "sample_scripts", "execution_flow"):
            self.assertIn(key, help_data)

    def test_api_reference_entries_have_required_keys(self):
        for entry in get_agent_help()["api_reference"]:
            self.assertIn("method", entry)
            self.assertIn("params", entry)
            self.assertIn("returns", entry)
            self.assertIn("description", entry)

    def test_api_reference_is_not_empty(self):
        self.assertTrue(len(get_agent_help()["api_reference"]) > 0)

    def test_sample_scripts_have_nonempty_code(self):
        samples = get_agent_help()["sample_scripts"]
        self.assertTrue(len(samples) > 0)
        for sample in samples:
            self.assertIn("title", sample)
            self.assertTrue(sample["code"].strip())

    def test_execution_flow_steps_are_ordered(self):
        steps = [f["step"] for f in get_agent_help()["execution_flow"]]
        self.assertEqual(steps, sorted(steps))


class AgentHelpPanelTemplateTest(TestCase):
    def test_panel_renders_with_help_context(self):
        html = render_to_string(
            "task_app/agent_help_panel.html",
            {"agent_help": get_agent_help()},
        )
        self.assertIn("Agent Script", html)
        self.assertIn("ctx.clone_git_url()", html)

    def test_panel_empty_without_help_context(self):
        html = render_to_string("task_app/agent_help_panel.html", {})
        self.assertNotIn("agent-help-panel", html)


class ProjectUpdateAgentHelpContextTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="owner", password="pass")
        self.project = Project.objects.create(name="P")
        self.project.participants.add(self.user)

    def test_update_get_includes_agent_help(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("project_update", kwargs={"pk": self.project.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("agent_help", response.context)
        self.assertIn("api_reference", response.context["agent_help"])
