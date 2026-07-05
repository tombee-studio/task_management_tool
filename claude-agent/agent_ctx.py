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

    def _complete_code(self, prompt):
        """Run Claude for a code-generation task and return the response text.

        Takes the fully-built system prompt (framing + codebase + FILE-block
        instructions).  Uses adaptive thinking + high effort (the biggest
        accuracy lever for Opus on coding) and a generous token budget,
        streamed so large full-file outputs are not truncated or timed out.
        Thinking blocks are skipped; only the visible text is returned.
        """
        with self._client.messages.stream(
            model=self._model,
            max_tokens=_CODE_MAX_TOKENS,
            system=prompt,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            message = stream.get_final_message()
        return "".join(
            block.text for block in message.content
            if getattr(block, "type", None) == "text"
        )

    def complete_text(self, prompt, max_tokens=2048, include_codebase=False):
        """Run Claude for a free-form text answer and return the text.

        Unlike _complete_code(), this uses no code-generation system prompt
        and does not ask for FILE blocks, so it is the right helper when an
        agent script needs plain text -- a summary, a title, a description.
        Calling _complete_code() for prose makes the model wrap its answer in
        a 'FILE: docs/design/*.md' block, which is almost never what a script
        building a task title or description wants.

        When include_codebase is True the cloned repository (file tree plus
        contents) is prepended to the prompt and the model is told to only
        reference paths that actually exist.  Without this grounding, prompts
        that ask for "the files to change" make the model invent plausible
        but non-existent paths (e.g. a React 'src/...tsx' layout for a Django
        project).  Requires clone_git_url() to have been called first.
        """
        if include_codebase:
            if self._workdir is None:
                raise RuntimeError(
                    "Call clone_git_url() before complete_text(include_codebase=True)."
                )
            context = self._read_codebase()
            prompt = (
                f"{prompt}\n\n"
                "Ground your answer in the actual repository below. When you "
                "name files to change, use real paths that exist in it; only "
                "introduce a new path if you explicitly say the file is new "
                "and place it consistent with the project's real structure. "
                "Do not invent paths for files you claim already exist.\n\n"
                f"{context}"
            )

        msg = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(
            block.text for block in msg.content
            if getattr(block, "type", None) == "text"
        ).strip()

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, path, params=None):
        resp = requests.get(f"{self._api_url}/{path}", headers=self._headers, params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path, data):
        resp = requests.post(f"{self._api_url}/{path}", headers=self._headers, json=data)
        resp.raise_for_status()
        return resp.json()

    def _patch(self, path, data):
        resp = requests.patch(f"{self._api_url}/{path}", headers=self._headers, json=data)
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path):
        """Issue an HTTP DELETE. Returns None (DELETE has no JSON body)."""
        resp = requests.delete(f"{self._api_url}/{path}", headers=self._headers)
        resp.raise_for_status()
        return None

    # ------------------------------------------------------------------
    # Shell / git helpers
    # ------------------------------------------------------------------

    def _run(self, cmd, cwd=None, check=True, env=None):
        return subprocess.run(
            cmd, cwd=cwd or self._workdir, check=check, text=True, capture_output=True, env=env
        )

    def _git(self, args, check=True):
        return self._run(["git"] + args, check=check)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_kinds(self):
        """Return list of TaskKind for the current project."""
        project = self._fetch_project()
        types = self._get("task_app/task-types/", params={"project": project["id"]})
        return [TaskKind(t["name"]) for t in types]

    def clone_git_url(self):
        """Clone the project's git_url to a temporary directory.

        Must be called before branch(), push(), or gh_create_pr().
        """
        project = self._fetch_project()
        git_url = (project.get("git_url") or "").rstrip("/").removesuffix(".git")
        if not git_url:
            raise RuntimeError("Project has no git_url set.")

        parsed = urlparse(git_url)
        self._github_repo = parsed.path.lstrip("/")
        self._github_remote = f"https://{self._github_pat}@{parsed.netloc}{parsed.path}.git"

        self._tmpdir = tempfile.TemporaryDirectory()
        self._workdir = self._tmpdir.name

        self._run(["git", "clone", self._github_remote, self._workdir], cwd=None)
        self._git(["config", "user.email", "claude-agent@example.com"])
        self._git(["config", "user.name", "Claude Agent"])
        print(f"[agent] Cloned {self._github_repo}")

    def get_task(self, task_id=None):
        """Fetch a task with comments. Returns TaskInfo.

        task_id defaults to the current task; pass an id to fetch any other task.
        """
        if task_id is None:
            task_id = self.task_id
        data = self._get(f"task_app/tasks/{task_id}/")

        kind_name = None
        if data.get("task_type"):
            try:
                tt = self._get(f"task_app/task-types/{data['task_type']}/")
                kind_name = tt.get("name", "")
            except Exception:
                pass

        comments_resp = requests.get(
            f"{self._api_url}/task_app/comments/",
            headers=self._headers,
            params={"task": task_id},
        )
        comments = comments_resp.json() if comments_resp.ok else []

        return TaskInfo(data, kind_name=kind_name, comments=comments)

    def update_task(self, task_id=None, **fields):
        """Update a task via the API. Returns the updated task dict.

        task_id defaults to the current task. Fields are passed as keyword
        arguments (e.g. update_task(status=4, assignee=3)).
        """
        if task_id is None:
            task_id = self.task_id
        result = self._patch(f"task_app/tasks/{task_id}/", fields)
        print(f"[agent] Updated task #{task_id}.")
        return result

    def delete_task(self, task_id):
        """Delete a task via the API."""
        self._delete(f"task_app/tasks/{task_id}/")
        print(f"[agent] Deleted task #{task_id}.")

    # --- Status CRUD ---------------------------------------------------

    def create_status(self, name, is_done=False, project=None):
        """Create a status via the API. Returns the created status id.

        `project` defaults to the current task's project.
        """
        if project is None:
            current = self._get(f"task_app/tasks/{self.task_id}/")
            project = current["project"]
        payload = {"name": name, "is_done": is_done, "project": project}
        result = self._post("task_app/statuses/", payload)
        print(f"[agent] Created status #{result['id']}: {name}")
        return result["id"]

    def get_status(self, status_id):
        """Fetch a status. Returns the status dict."""
        return self._get(f"task_app/statuses/{status_id}/")

    def update_status(self, status_id, **fields):
        """Update a status via the API. Returns the updated status dict."""
        return self._patch(f"task_app/statuses/{status_id}/", fields)

    def delete_status(self, status_id):
        """Delete a status via the API."""
        self._delete(f"task_app/statuses/{status_id}/")

    # --- Comment CRUD --------------------------------------------------

    def create_comment(self, description, task=None, author=None):
        """Create a comment via the API. Returns the created comment id.

        `task` defaults to the current task; `author` defaults to the current
        task's assignee.
        """
        if task is None or author is None:
            current = self._get(f"task_app/tasks/{self.task_id}/")
            if task is None:
                task = self.task_id
            if author is None:
                author = current.get("assignee")
        payload = {"description": description, "task": task, "author": author}
        result = self._post("task_app/comments/", payload)
        print(f"[agent] Created comment #{result['id']} on task #{task}.")
        return result["id"]

    def get_comment(self, comment_id):
        """Fetch a comment. Returns the comment dict."""
        return self._get(f"task_app/comments/{comment_id}/")

    def update_comment(self, comment_id, **fields):
        """Update a comment via the API. Returns the updated comment dict."""
        return self._patch(f"task_app/comments/{comment_id}/", fields)

    def delete_comment(self, comment_id):
        """Delete a comment via the API."""
        self._delete(f"task_app/comments/{comment_id}/")

    # --- Event CRUD ----------------------------------------------------

    def create_event(self, event_date, name=None, project=None,
                     participant_count=None, status=None, previous_event=None):
        """Create an event via the API. Returns the created event id.

        `project` defaults to the current task's project. Other optional
        fields are only sent when provided.
        """
        if project is None:
            current = self._get(f"task_app/tasks/{self.task_id}/")
            project = current["project"]
        payload = {"event_date": event_date, "project": project}
        optional = {
            "name": name,
            "participant_count": participant_count,
            "status": status,
            "previous_event": previous_event,
        }
        payload.update({k: v for k, v in optional.items() if v is not None})
        result = self._post("event_app/events/", payload)
        print(f"[agent] Created event #{result['id']}.")
        return result["id"]

    def get_event(self, event_id):
        """Fetch an event. Returns the event dict."""
        return self._get(f"event_app/events/{event_id}/")

    def update_event(self, event_id, **fields):
        """Update an event via the API. Returns the updated event dict."""
        return self._patch(f"event_app/events/{event_id}/", fields)

    def delete_event(self, event_id):
        """Delete an event via the API."""
        self._delete(f"event_app/events/{event_id}/")

    # --- DSL -----------------------------------------------------------

    def execute_dsl(self, dsl):
        """Execute a DSL script server-side via the API.

        Returns the number of executed commands (executed_count).
        """
        result = self._post("task_app/dsl/execute/", {"dsl": dsl})
        count = result.get("executed_count", 0)
        print(f"[agent] Executed DSL ({count} command(s)).")
        return count

    def decide_strategy(self, task, kinds):
        """Ask Claude to plan the implementation.

        Stores the strategy internally (used by push()).
        Returns a Strategy instance.
        """
        kinds_text = ", ".join(k.name for k in kinds) if kinds else "(none)"

        msg = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": (
                    "You are a software architect. Given the task below, output a JSON object with:\n"
                    "- approach: string describing how to implement the task\n"
                    "- subtask_titles: list of strings (empty list if no subtasks are needed)\n\n"
                    f"Task #{task.id}: {task.title}\n"
                    f"Description: {task.description}\n"
                    f"Available task kinds: {kinds_text}\n\n"
                    "Reply with ONLY a JSON object, no markdown fences."
                ),
            }],
        )

        raw = msg.content[0].text.strip()
        raw = re.sub(r"^