"""AgentCtx — context object for dynamic Claude agent scripts.

Usage in an agent script stored in Project.agent:

    ctx.clone_git_url()
    task = ctx.get_task()
    kinds = ctx.get_kinds()
    strategy = ctx.decide_strategy(task, kinds)
    if ctx.get_modification_level() > MIDDLE:
        ctx.create_subtasks(strategy)
    ctx.branch(task)
    ctx.push(task)
    ctx.gh_create_pr(task)
    ctx.change_assignee(ctx.get_assignee())
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

import anthropic
import requests

# Modification level constants available in agent scripts
SMALL = 1
MIDDLE = 2
LARGE = 3

# Code-generation tuning.  The previous 8K cap silently truncated full-file
# rewrites mid-output, which was the main cause of broken/inaccurate edits.
# Large outputs require streaming to avoid SDK HTTP timeouts.
_CODE_MAX_TOKENS = 64000

_KIND_PREFIX = {"feature": "Ftr", "bugfix": "Fix", "hotfix": "Fix", "enhancement": "Eta"}
_KIND_MAP = {"bug": "bugfix", "feature": "feature", "enhancement": "enhancement", "hotfix": "hotfix"}


class TaskKind:
    """Represents a task type/kind."""

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"TaskKind({self.name!r})"


class TaskInfo:
    """Task data as returned by AgentCtx.get_task()."""

    def __init__(self, data, kind_name=None, comments=None):
        self.id = data["id"]
        self.title = data["title"]
        self.description = data.get("description", "")
        self.status = data.get("status")
        self.assignee = data.get("assignee")
        self.reporter = data.get("reporter")
        self.parent = data.get("parent")
        self.project = data.get("project")
        self.event = data.get("event")
        self.comments = comments or []
        self.kind = TaskKind(kind_name) if kind_name else None
        self._raw = data


class Strategy:
    """Implementation strategy returned by AgentCtx.decide_strategy()."""

    def __init__(self, approach, subtask_titles=None):
        self.approach = approach
        self.subtask_titles = subtask_titles or []


class AgentCtx:
    """Provides all agent operations for use in dynamic agent scripts.

    Instantiate once per agent run.  Call clone_git_url() before any
    git operations.
    """

    def __init__(self, task_id, api_url, api_key, github_pat, anthropic_api_key,
                 model="claude-sonnet-4-6"):
        self.task_id = task_id
        self._api_url = api_url.rstrip("/")
        self._api_key = api_key
        self._github_pat = github_pat
        self._model = model
        self._anthropic_api_key = anthropic_api_key
        self._claude = None          # lazy-init Anthropic client
        self._workdir = None         # set by clone_git_url()
        self._tmpdir = None          # TemporaryDirectory handle
        self._project = None         # cached project dict
        self._branch = None          # set by branch()
        self._kind = None            # set by branch()
        self._strategy = None        # set by decide_strategy()
        self._github_repo = None     # set by clone_git_url()
        self._github_remote = None   # set by clone_git_url()
        self._headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

    # ------------------------------------------------------------------
    # Anthropic client (lazy)
    # ------------------------------------------------------------------

    @property
    def _client(self):
        if self._claude is None:
            self._claude = anthropic.Anthropic(api_key=self._anthropic_api_key)
        return self._claude

    def _complete_code(self, context, prompt):
        """Run Claude for a code-generation task and return the response text.

        Uses adaptive thinking + high effort (the biggest accuracy lever for
        Opus on coding) and a generous token budget, streamed so large
        full-file outputs are not truncated or timed out.  Thinking blocks are
        skipped; only the visible text is returned.
        """
        full_prompt = (
            f"{prompt.strip()}\n\n"
            f"Here is the relevant codebase:\n{context}\n\n"
            "Provide the complete content of each file you need to create or modify. "
            "Format each file as:\n"
            "FILE: <relative/path/to/file>\n