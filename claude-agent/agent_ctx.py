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

    def get_task(self):
        """Fetch the current task with comments. Returns TaskInfo."""
        data = self._get(f"task_app/tasks/{self.task_id}/")

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
            params={"task": self.task_id},
        )
        comments = comments_resp.json() if comments_resp.ok else []

        return TaskInfo(data, kind_name=kind_name, comments=comments)

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
        raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw)

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"approach": raw, "subtask_titles": []}

        strategy = Strategy(
            approach=payload.get("approach", ""),
            subtask_titles=payload.get("subtask_titles", []),
        )
        self._strategy = strategy
        return strategy

    def get_modification_level(self):
        """Ask Claude to assess implementation scope.

        Returns SMALL (1), MIDDLE (2), or LARGE (3).
        """
        data = self._get(f"task_app/tasks/{self.task_id}/")

        msg = self._client.messages.create(
            model=self._model,
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": (
                    f"Task: {data['title']}\n"
                    f"Description: {data.get('description', '')}\n\n"
                    "Reply with exactly one word: SMALL, MIDDLE, or LARGE, "
                    "based on how much code change is required."
                ),
            }],
        )

        word = msg.content[0].text.strip().upper()
        return {"SMALL": SMALL, "MIDDLE": MIDDLE, "LARGE": LARGE}.get(word, MIDDLE)

    def create_subtasks(self, strategy):
        """Create subtasks listed in strategy.subtask_titles.

        Returns list of created task IDs.
        """
        data = self._get(f"task_app/tasks/{self.task_id}/")
        created = []
        for title in (strategy.subtask_titles or []):
            result = self._post("task_app/tasks/", {
                "title": title,
                "project": data["project"],
                "parent": self.task_id,
                "event": data.get("event"),
                "assignee": data["assignee"],
                "status": 1,
            })
            created.append(result["id"])
            print(f"[agent] Created subtask #{result['id']}: {title}")
        return created

    def branch(self, task):
        """Create or switch to the appropriate git branch for the task."""
        if self._workdir is None:
            raise RuntimeError("Call clone_git_url() before branch().")

        kind = self._classify_kind(task)
        self._kind = kind
        branch_name = self._make_branch_name(kind, task)
        self._branch = branch_name

        if self._git(["checkout", branch_name], check=False).returncode != 0:
            self._git(["checkout", "-b", branch_name])

        print(f"[agent] On branch {branch_name}")

    def post_comment(self, task, message):
        """Post a comment on the task."""
        task_id = task.id if isinstance(task, TaskInfo) else task["id"]
        author_id = task.assignee if isinstance(task, TaskInfo) else task["assignee"]
        try:
            self._post("task_app/comments/", {
                "author": author_id,
                "description": message,
                "task": task_id,
            })
            print(f"[agent] Posted comment on task #{task_id}.")
        except Exception as e:
            print(f"[agent] Failed to post comment: {e}", file=sys.stderr)

    def change_assignee(self, assignee_id):
        """Change the assignee of the current task."""
        self._patch(f"task_app/tasks/{self.task_id}/", {"assignee": assignee_id})
        print(f"[agent] Changed assignee to {assignee_id}.")

    def get_assignee(self):
        """Return the reporter ID (typically restored as assignee on completion)."""
        data = self._get(f"task_app/tasks/{self.task_id}/")
        return data.get("reporter") or data.get("assignee")

    def run_agent(self, prompt):
        """Run Claude with *prompt* in the current working-directory context.

        Reads the codebase, asks Claude to implement the changes described in
        *prompt*, applies any FILE blocks returned, and returns the list of
        changed file paths.  Call clone_git_url() before run_agent().
        """
        if self._workdir is None:
            raise RuntimeError("Call clone_git_url() before run_agent().")

        context = self._read_codebase()
        full_prompt = (
            f"{prompt.strip()}\n\n"
            f"Here is the relevant codebase:\n{context}\n\n"
            "Provide the complete content of each file you need to create or modify. "
            "Format each file as:\n"
            "FILE: <relative/path/to/file>\n```\n<content>\n```\n\n"
            "Only output FILE blocks. No explanations."
        )

        print("[agent] run_agent: calling Claude...")
        response = self._client.messages.create(
            model=self._model,
            max_tokens=8096,
            messages=[{"role": "user", "content": full_prompt}],
        )
        implementation = response.content[0].text

        changed_files = self._apply_files(implementation)
        print(f"[agent] run_agent: {len(changed_files)} file(s) changed.")
        return changed_files

    def push(self, task):
        """Ask Claude to implement the task, run tests, commit, and push.

        Uses the strategy stored by decide_strategy() if available.
        Updates task status to レビュー (4) and posts a completion comment.
        Returns the commit SHA.
        """
        if self._workdir is None:
            raise RuntimeError("Call clone_git_url() before push().")
        if self._branch is None:
            raise RuntimeError("Call branch() before push().")

        task_id = task.id if isinstance(task, TaskInfo) else task["id"]
        title = task.title if isinstance(task, TaskInfo) else task["title"]
        description = task.description if isinstance(task, TaskInfo) else task.get("description", "")
        comments = task.comments if isinstance(task, TaskInfo) else []

        context = self._read_codebase()
        comments_text = (
            "\n".join(f"[Comment #{c['id']}] {c['description']}" for c in comments)
            if comments else "(no comments)"
        )

        prompt = (
            "You are an expert Django developer working on the task-management project.\n\n"
            f"Task #{task_id}: {title}\n"
            f"Description:\n{description}\n\n"
        )
        if self._strategy:
            prompt += f"Implementation plan:\n{self._strategy.approach}\n\n"
        prompt += (
            f"Comments on this task:\n{comments_text}\n\n"
            "CLAUDE.md workflow is in the repo. Follow it.\n\n"
            f"Here is the relevant codebase:\n{context}\n\n"
            "Provide the complete content of each file you need to create or modify. "
            "Format each file as:\n"
            "FILE: <relative/path/to/file>\n```\n<content>\n```\n\n"
            "Only output FILE blocks. No explanations."
        )

        print(f"[agent] Calling Claude for task #{task_id}...")
        response = self._client.messages.create(
            model=self._model,
            max_tokens=8096,
            messages=[{"role": "user", "content": prompt}],
        )
        implementation = response.content[0].text

        changed_files = self._apply_files(implementation)
        if not changed_files:
            raise RuntimeError(
                "No files were changed. The agent could not determine what to implement."
            )

        self._run_tests()

        prefix = _KIND_PREFIX.get(self._kind, "Ftr")
        commit_msg = f"{prefix}: {title[:44]} #{task_id}"[:50] + f"\n\nTask: {task_id}"
        self._git(["add", "-A"])
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=self._workdir,
            env={**os.environ, "TASK_URL": f"{self._api_url}/task_app/tasks"},
            check=True,
        )

        commit_sha = self._git(["rev-parse", "HEAD"]).stdout.strip()
        self._git(["push", "-u", "origin", self._branch])

        review_patch = {"status": 4}
        task_data = self._get(f"task_app/tasks/{task_id}/")
        if task_data.get("reporter"):
            review_patch["assignee"] = task_data["reporter"]
        self._patch(f"task_app/tasks/{task_id}/", review_patch)
        print(f"[agent] Task #{task_id} marked as review.")

        commit_url = f"https://github.com/{self._github_repo}/commit/{commit_sha}"
        self.post_comment(task, f"対応コミット: [{commit_sha[:8]}]({commit_url})")
        self.post_comment(task, "対応が完了しました。")

        return commit_sha

    def git_push(self, task):
        """Alias for push()."""
        return self.push(task)

    def gh_create_pr(self, task):
        """Create a GitHub PR for the current branch."""
        if self._branch is None:
            raise RuntimeError("Call branch() before gh_create_pr().")

        task_id = task.id if isinstance(task, TaskInfo) else task["id"]
        title = task.title if isinstance(task, TaskInfo) else task["title"]

        project = self._fetch_project()
        base = self._resolve_base_branch(project)
        prefix = _KIND_PREFIX.get(self._kind, "Ftr")

        pr_resp = requests.post(
            f"https://api.github.com/repos/{self._github_repo}/pulls",
            headers={
                "Authorization": f"token {self._github_pat}",
                "Accept": "application/vnd.github.v3+json",
            },
            json={
                "title": f"{prefix}: {title[:60]} #{task_id}",
                "head": self._branch,
                "base": base,
                "body": f"Task: {task_id}",
            },
        )

        if pr_resp.status_code == 201:
            pr_data = pr_resp.json()
            pr_url = pr_data["html_url"]
            pr_number = pr_data["number"]
            print(f"[agent] PR created: {pr_url}")

            task_data = self._get(f"task_app/tasks/{task_id}/")
            existing_desc = (task_data.get("description") or "").strip()
            pr_link = f"[PR #{pr_number}]({pr_url})"
            new_desc = f"{existing_desc}\n\n{pr_link}" if existing_desc else pr_link
            self._patch(f"task_app/tasks/{task_id}/", {"description": new_desc})
            return pr_data

        print(f"[agent] PR creation failed: {pr_resp.status_code} {pr_resp.text}", file=sys.stderr)
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_project(self):
        if self._project is None:
            task = self._get(f"task_app/tasks/{self.task_id}/")
            self._project = self._get(f"task_app/projects/{task['project']}/")
        return self._project

    def _resolve_base_branch(self, project):
        candidates = []
        dev = (project.get("dev_branch") or "").strip()
        if dev:
            candidates.append(dev)
        main = (project.get("main_branch") or "").strip()
        if main:
            candidates.append(main)

        gh_headers = {
            "Authorization": f"token {self._github_pat}",
            "Accept": "application/vnd.github.v3+json",
        }

        repo_resp = requests.get(
            f"https://api.github.com/repos/{self._github_repo}",
            headers=gh_headers,
        )
        default_branch = repo_resp.json().get("default_branch", "main") if repo_resp.ok else "main"

        for candidate in candidates:
            check = requests.get(
                f"https://api.github.com/repos/{self._github_repo}/branches/{candidate}",
                headers=gh_headers,
            )
            if check.status_code == 200:
                return candidate
            print(f"[agent] Branch '{candidate}' not found in repo, skipping.")

        print(f"[agent] Falling back to default branch '{default_branch}'.")
        return default_branch

    def _classify_kind(self, task):
        for tag in (getattr(task, "_raw", {}).get("tags") or []):
            name = tag if isinstance(tag, str) else tag.get("name", "")
            if name in _KIND_MAP:
                return _KIND_MAP[name]

        if task.kind and task.kind.name:
            n = task.kind.name.lower()
            for k, v in _KIND_MAP.items():
                if k in n:
                    return v

        msg = self._client.messages.create(
            model=self._model,
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": (
                    f"Task title: {task.title}\n"
                    f"Description: {task.description}\n\n"
                    "Reply with exactly one word — the git branch kind: "
                    "feature, bugfix, hotfix, or enhancement."
                ),
            }],
        )
        word = msg.content[0].text.strip().lower()
        return word if word in ("feature", "bugfix", "hotfix", "enhancement") else "feature"

    def _make_branch_name(self, kind, task):
        try:
            task.title.encode("ascii")
            slug = re.sub(r"[^a-z0-9]+", "-", task.title.lower()).strip("-")[:40] or "task"
        except UnicodeEncodeError:
            msg = self._client.messages.create(
                model=self._model,
                max_tokens=30,
                messages=[{
                    "role": "user",
                    "content": (
                        "Convert this task title to a short English slug for a git branch.\n"
                        "Rules: lowercase ASCII, digits, hyphens only; max 40 chars.\n"
                        f"Task title: {task.title}\n\nReply with ONLY the slug."
                    ),
                }],
            )
            raw = msg.content[0].text.strip().lower()
            slug = re.sub(r"[^a-z0-9-]", "-", raw)
            slug = re.sub(r"-{2,}", "-", slug).strip("-")[:40] or "task"
        return f"{kind}/#{task.id}_{slug}"

    def _read_codebase(self):
        context_files = []
        for root, dirs, files in os.walk(self._workdir):
            dirs[:] = [d for d in dirs
                       if d not in {".git", "venv", "__pycache__", ".venv", "node_modules"}]
            for f in files:
                if f.endswith((".py", ".tf", ".md", ".lark")) and "migrations" not in root:
                    path = os.path.join(root, f)
                    rel = os.path.relpath(path, self._workdir)
                    try:
                        with open(path) as fh:
                            content = fh.read()
                        context_files.append(f"### {rel}\n```\n{content}\n```")
                    except Exception:
                        pass
        return "\n\n".join(context_files[:60])

    def _apply_files(self, implementation):
        file_pattern = re.compile(r"FILE:\s*(\S+)\n```(?:\w*)\n(.*?)```", re.DOTALL)
        changed = []
        for match in file_pattern.finditer(implementation):
            rel_path, content = match.group(1).strip("`"), match.group(2)
            abs_path = os.path.join(self._workdir, rel_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w") as fh:
                fh.write(content)
            changed.append(rel_path)
            print(f"[agent] Wrote {rel_path}")
        return changed

    def _run_tests(self):
        django_dir = os.path.join(self._workdir, "django-app")
        if not os.path.isdir(django_dir):
            print("[agent] No django-app/ — skipping tests.")
            return
        self._run(["pip", "install", "-q", "-r", "requirements.txt"], cwd=django_dir, check=False)
        result = self._run(
            ["python", "manage.py", "test", "task_app", "event_app", "--verbosity=1"],
            cwd=django_dir,
            check=False,
            env={**os.environ, "DJANGO_SETTINGS_MODULE": "task_management.test_settings"},
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Tests failed.\n\n```\n{result.stdout[-2000:]}\n{result.stderr[-1000:]}\n```"
            )
        print("[agent] Tests passed.")

    def __del__(self):
        if self._tmpdir is not None:
            try:
                self._tmpdir.cleanup()
            except Exception:
                pass
