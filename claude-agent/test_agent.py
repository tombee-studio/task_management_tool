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
    def test_uses_task_type_agent_when_set(self, mock_get):
        mock_get.return_value = _resp({"agent": "TT SCRIPT"})
        script, source = agent._resolve_agent_script({"task_type": 7})
        self.assertEqual(script, "TT SCRIPT")
        self.assertEqual(source, "task-type")

    @patch("agent.requests.get")
    def test_defaults_when_task_type_agent_empty(self, mock_get):
        mock_get.return_value = _resp({"agent": "  "})
        script, source = agent._resolve_agent_script({"task_type": 7})
        self.assertEqual(script, agent.DEFAULT_AGENT_SCRIPT)
        self.assertEqual(source, "default")

    @patch("agent.requests.get")
    def test_defaults_when_task_type_fetch_fails(self, mock_get):
        mock_get.return_value = _resp({}, ok=False)
        script, source = agent._resolve_agent_script({"task_type": 7})
        self.assertEqual(script, agent.DEFAULT_AGENT_SCRIPT)
        self.assertEqual(source, "default")

    def test_defaults_when_no_task_type(self):
        script, source = agent._resolve_agent_script({"task_type": None})
        self.assertEqual(script, agent.DEFAULT_AGENT_SCRIPT)
        self.assertEqual(source, "default")


def _dispatch(status_agents, task_type):
    """Return a requests.get side_effect dispatching on the URL."""
    def _get(url, *args, **kwargs):
        if "task-type-status-agents" in url:
            return _resp(status_agents)
        return _resp(task_type)
    return _get


class TestResolveAgentScriptWithStatus(unittest.TestCase):
    @patch("agent.requests.get")
    def test_uses_status_agent_when_set(self, mock_get):
        mock_get.side_effect = _dispatch(
            status_agents=[{"agent": "STATUS SCRIPT"}],
            task_type={"agent": "TT SCRIPT"},
        )
        script, source = agent._resolve_agent_script({"task_type": 7, "status": 4})
        self.assertEqual(script, "STATUS SCRIPT")
        self.assertEqual(source, "task-type+status")

    @patch("agent.requests.get")
    def test_falls_back_to_task_type_when_no_status_agent(self, mock_get):
        mock_get.side_effect = _dispatch(
            status_agents=[],
            task_type={"agent": "TT SCRIPT"},
        )
        script, source = agent._resolve_agent_script({"task_type": 7, "status": 4})
        self.assertEqual(script, "TT SCRIPT")
        self.assertEqual(source, "task-type")

    @patch("agent.requests.get")
    def test_falls_back_when_status_agent_blank(self, mock_get):
        mock_get.side_effect = _dispatch(
            status_agents=[{"agent": "   "}],
            task_type={"agent": "TT SCRIPT"},
        )
        script, source = agent._resolve_agent_script({"task_type": 7, "status": 4})
        self.assertEqual(script, "TT SCRIPT")
        self.assertEqual(source, "task-type")

    @patch("agent.requests.get")
    def test_defaults_when_neither_set(self, mock_get):
        mock_get.side_effect = _dispatch(status_agents=[], task_type={"agent": ""})
        script, source = agent._resolve_agent_script({"task_type": 7, "status": 4})
        self.assertEqual(script, agent.DEFAULT_AGENT_SCRIPT)
        self.assertEqual(source, "default")


if __name__ == "__main__":
    unittest.main(verbosity=2)
