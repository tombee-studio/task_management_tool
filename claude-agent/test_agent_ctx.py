"""Unit tests for AgentCtx.

All external calls (API, Claude, git) are mocked — no real Claude Agent is invoked.
Run with:
    python -m pytest test_agent_ctx.py -v
or:
    python -m unittest test_agent_ctx -v
"""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from agent_ctx import AgentCtx, Strategy, TaskInfo, TaskKind, SMALL, MIDDLE, LARGE


def _make_ctx(**kwargs):
    defaults = dict(
        task_id=123,
        api_url="https://api.example.com",
        api_key="test-key",
        github_pat="test-pat",
        anthropic_api_key="test-anthropic-key",
        model="claude-test",
    )
    defaults.update(kwargs)
    return AgentCtx(**defaults)


def _mock_response(data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = status_code < 400
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


def _task_info(**overrides):
    data = {
        "id": 123, "title": "T", "description": "", "status": 1,
        "assignee": 2, "reporter": None, "parent": None,
        "project": 1, "event": None,
    }
    data.update(overrides)
    return TaskInfo(data)


class TestModificationLevelConstants(unittest.TestCase):
    def test_ordering(self):
        self.assertLess(SMALL, MIDDLE)
        self.assertLess(MIDDLE, LARGE)

    def test_values(self):
        self.assertEqual(SMALL, 1)
        self.assertEqual(MIDDLE, 2)
        self.assertEqual(LARGE, 3)


class TestTaskInfo(unittest.TestCase):
    def test_fields(self):
        data = {
            "id": 10, "title": "Fix bug", "description": "desc",
            "status": 2, "assignee": 5, "reporter": 3,
            "parent": None, "project": 1, "event": None,
        }
        info = TaskInfo(data, kind_name="feature", comments=[{"id": 1, "description": "ok"}])
        self.assertEqual(info.id, 10)
        self.assertEqual(info.title, "Fix bug")
        self.assertEqual(info.kind.name, "feature")
        self.assertEqual(len(info.comments), 1)

    def test_no_kind(self):
        data = {"id": 1, "title": "T", "description": "", "status": 1,
                "assignee": 1, "reporter": None, "parent": None, "project": 1, "event": None}
        info = TaskInfo(data)
        self.assertIsNone(info.kind)


class TestTaskKind(unittest.TestCase):
    def test_name(self):
        k = TaskKind("issue")
        self.assertEqual(k.name, "issue")


class TestStrategy(unittest.TestCase):
    def test_defaults(self):
        s = Strategy("do something")
        self.assertEqual(s.approach, "do something")
        self.assertEqual(s.subtask_titles, [])

    def test_subtasks(self):
        s = Strategy("plan", ["Sub A", "Sub B"])
        self.assertEqual(len(s.subtask_titles), 2)


class TestGetKinds(unittest.TestCase):
    @patch("agent_ctx.requests.get")
    def test_returns_task_kind_list(self, mock_get):
        task_data = {"id": 123, "project": 1, "title": "T", "assignee": 2}
        project_data = {"id": 1, "name": "Proj", "git_url": "https://github.com/o/r",
                        "dev_branch": "develop", "main_branch": "main", "agent": ""}
        kinds_data = [{"id": 1, "name": "feature"}, {"id": 2, "name": "bugfix"}]

        mock_get.side_effect = [
            _mock_response(task_data),
            _mock_response(project_data),
            _mock_response(kinds_data),
        ]

        ctx = _make_ctx()
        kinds = ctx.get_kinds()

        self.assertEqual(len(kinds), 2)
        self.assertIsInstance(kinds[0], TaskKind)
        self.assertEqual(kinds[0].name, "feature")
        self.assertEqual(kinds[1].name, "bugfix")


class TestGetTask(unittest.TestCase):
    @patch("agent_ctx.requests.get")
    def test_returns_task_info_with_kind(self, mock_get):
        task_data = {
            "id": 123, "title": "Add feature", "description": "desc",
            "status": 1, "assignee": 2, "reporter": 3,
            "parent": None, "project": 1, "event": 5, "task_type": 7,
        }
        task_type_data = {"id": 7, "name": "feature"}
        comments_data = [{"id": 9, "description": "looks good"}]

        mock_get.side_effect = [
            _mock_response(task_data),
            _mock_response(task_type_data),
            _mock_response(comments_data),
        ]

        ctx = _make_ctx()
        task = ctx.get_task()

        self.assertIsInstance(task, TaskInfo)
        self.assertEqual(task.id, 123)
        self.assertEqual(task.title, "Add feature")
        self.assertIsNotNone(task.kind)
        self.assertEqual(task.kind.name, "feature")
        self.assertEqual(len(task.comments), 1)

    @patch("agent_ctx.requests.get")
    def test_returns_task_info_without_kind(self, mock_get):
        task_data = {
            "id": 123, "title": "T", "description": "", "status": 1,
            "assignee": 2, "reporter": None, "parent": None,
            "project": 1, "event": None, "task_type": None,
        }
        comments_resp = _mock_response([])

        mock_get.side_effect = [
            _mock_response(task_data),
            comments_resp,
        ]

        ctx = _make_ctx()
        task = ctx.get_task()
        self.assertIsNone(task.kind)

    @patch("agent_ctx.requests.get")
    def test_fetches_explicit_task_id(self, mock_get):
        # ctx is for task 123 but we ask for task 456.
        task_data = {
            "id": 456, "title": "Other", "description": "", "status": 1,
            "assignee": 2, "reporter": None, "parent": None,
            "project": 1, "event": None, "task_type": None,
        }
        mock_get.side_effect = [
            _mock_response(task_data),
            _mock_response([]),
        ]

        ctx = _make_ctx()
        task = ctx.get_task(456)

        self.assertEqual(task.id, 456)
        # The task and comments requests must target task 456, not 123.
        self.assertIn("task_app/tasks/456/", mock_get.call_args_list[0][0][0])
        self.assertEqual(mock_get.call_args_list[1][1]["params"], {"task": 456})


class TestDecideStrategy(unittest.TestCase):
    def _make_claude_mock(self, response_text):
        content = MagicMock()
        content.text = response_text
        message = MagicMock()
        message.content = [content]
        client = MagicMock()
        client.messages.create.return_value = message
        return client

    def test_parses_json_response(self):
        payload = json.dumps({
            "approach": "Add a new field to the model",
            "subtask_titles": ["Backend", "Frontend"],
        })
        ctx = _make_ctx()
        ctx._claude = self._make_claude_mock(payload)

        task = TaskInfo(
            {"id": 1, "title": "T", "description": "D", "status": 1,
             "assignee": 1, "reporter": None, "parent": None, "project": 1, "event": None}
        )
        kinds = [TaskKind("feature"), TaskKind("bugfix")]

        strategy = ctx.decide_strategy(task, kinds)

        self.assertIsInstance(strategy, Strategy)
        self.assertEqual(strategy.approach, "Add a new field to the model")
        self.assertEqual(strategy.subtask_titles, ["Backend", "Frontend"])
        self.assertIs(ctx._strategy, strategy)

    def test_handles_non_json_response(self):
        ctx = _make_ctx()
        ctx._claude = self._make_claude_mock("Just do it directly.")

        task = TaskInfo(
            {"id": 1, "title": "T", "description": "", "status": 1,
             "assignee": 1, "reporter": None, "parent": None, "project": 1, "event": None}
        )
        strategy = ctx.decide_strategy(task, [])

        self.assertEqual(strategy.approach, "Just do it directly.")
        self.assertEqual(strategy.subtask_titles, [])

    def test_strips_markdown_fences(self):
        payload = "