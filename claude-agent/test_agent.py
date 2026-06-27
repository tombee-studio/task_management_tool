"""Unit tests for agent.py script resolution.

External calls are mocked. Required environment variables are set before
importing agent, since the module reads them at import time.
"""
import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("TASK_ID", "1")
os.environ.setdefault("TASK_API_URL", "https://api.example.com")
os.environ.setdefault("TASK_API_KEY", "test-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic")
os.environ.setdefault("GITHUB_PAT", "test-pat")

import agent  # noqa: E402


def _resp(data, ok=True):
    r = MagicMock()
    r.ok = ok
    r.json.return_value = data
    return r


class TestResolveAgentScript(unittest.TestCase):
    @patch("agent.requests.get")
    def test_prefers_task_type_agent(self, mock_get):
        mock_get.return_value = _resp({"agent": "TT SCRIPT"})
        script, source = agent._resolve_agent_script(
            {"task_type": 7}, {"agent": "PROJECT SCRIPT"}
        )
        self.assertEqual(script, "TT SCRIPT")
        self.assertEqual(source, "task-type")

    @patch("agent.requests.get")
    def test_falls_back_to_project_when_task_type_agent_empty(self, mock_get):
        mock_get.return_value = _resp({"agent": "  "})
        script, source = agent._resolve_agent_script(
            {"task_type": 7}, {"agent": "PROJECT SCRIPT"}
        )
        self.assertEqual(script, "PROJECT SCRIPT")
        self.assertEqual(source, "project")

    @patch("agent.requests.get")
    def test_falls_back_to_project_when_task_type_fetch_fails(self, mock_get):
        mock_get.return_value = _resp({}, ok=False)
        script, source = agent._resolve_agent_script(
            {"task_type": 7}, {"agent": "PROJECT SCRIPT"}
        )
        self.assertEqual(script, "PROJECT SCRIPT")
        self.assertEqual(source, "project")

    def test_uses_project_when_no_task_type(self):
        script, source = agent._resolve_agent_script(
            {"task_type": None}, {"agent": "PROJECT SCRIPT"}
        )
        self.assertEqual(script, "PROJECT SCRIPT")
        self.assertEqual(source, "project")

    @patch("agent.requests.get")
    def test_uses_default_when_nothing_set(self, mock_get):
        mock_get.return_value = _resp({"agent": ""})
        script, source = agent._resolve_agent_script({"task_type": 7}, {"agent": ""})
        self.assertEqual(script, agent.DEFAULT_AGENT_SCRIPT)
        self.assertEqual(source, "default")


if __name__ == "__main__":
    unittest.main(verbosity=2)
