"""Claude automation agent.

Reads TASK_ID from the environment, fetches the task from the API,
uses Claude to implement the required change, runs tests, commits,
pushes, merges to develop, and updates the task status.

If the project has an `agent` field set, its content is treated as a
Python script (parsed via ast.parse) and executed to drive the agent's
behaviour instead of the built-in default pipeline.

Available names inside an agent script:
  task_id   -- int, the current task ID
  task      -- dict, the current task data
  project   -- dict, the current project data
  run_agent(task_id=None)         -- implement a task with Claude
  create_pr(task_id=None, **kw)   -- create a GitHub PR
  add_subtask(title, **kw)        -- create a subtask under the current task
"""
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

import anthropic
import requests

# ---------------------------------------------------------------------------
# Config from environment
# ---------------------------------------------------------------------------

TASK_ID = int(os.environ["TASK_ID"])
TASK_API_URL = os.environ["TASK_API_URL"].rstrip("/")
TASK_API_KEY = os.environ["TASK_API_KEY"]
TASK_STATUS_MERGE_ID = int(os.environ.get("TASK_STAUS_MERGE_ID", "12"))
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GITHUB_PAT = os.environ["GITHUB_PAT"]
REPORTER_ID = int(os.environ["REPORTER_ID"]) if os.environ.get("REPORTER_ID") else None
MODEL = "claude-sonnet-4-6"

api_headers = {"X-API-Key": TASK_API_KEY, "Content-Type": "application/json"}

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def api_get(path):
    resp = requests.get(f"{TASK_API_URL}/{path}", headers=api_headers)
    resp.raise_for_status()
    return resp.json()


def api_patch(path, data):
    resp = requests.patch(f"{TASK_API_URL}/{path}", headers=api_headers, json=data)
    resp.raise_for_status()
    return resp.json()


def api_post(path, data):
    resp = requests.post(f"{TASK_API_URL}/{path}", headers=api_headers, json=data)
    resp.raise_for_status()
    return resp.json()

# ---------------------------------------------------------------------------
# Comment helpers
# ---------------------------------------------------------------------------

def post_comment(task_id, author_id, text):
    try:
        api_post("task_app/comments/", {
            "author": author_id,
            "description": text,
            "task": task_id,
        })
        print(f"[agent] Posted comment on task #{task_id}.")
    except Exception as e:
        print(f"[agent] Failed to post comment on task #{task_id}: {e}", file=sys.stderr)


def post_commit_comment(task_id, commit_sha, github_repo, author_id):
    commit_url = f"https://github.com/{github_repo}/commit/{commit_sha}"
    post_comment(task_id, author_id, f"対応コミット: [{commit_sha[:8]}]({commit_url})")


def post_error_comment(task, error_text):
    try:
        api_post("task_app/comments/", {
            "author": task["assignee"],
            "description": f"[Automation Error]\n\n{error_text}",
            "task": task["id"],
        })
    except Exception as e:
        print(f"[agent] Failed to post error comment: {e}", file=sys.stderr)
    if task.get("reporter"):
        try:
            api_patch(f"task_app/tasks/{task['id']}/", {"assignee": task["reporter"]})
        except Exception as e:
            print(f"[agent] Failed to restore assignee: {e}", file=sys.stderr)

# ---------------------------------------------------------------------------
# Git / branch helpers
# ---------------------------------------------------------------------------

def run(cmd, cwd=None, check=True, env=None):
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True, env=env)


def git(args, cwd, check=True):
    return run(["git"] + args, cwd=cwd, check=check)


def resolve_base_branch(project, github_repo):
    dev = (project.get("dev_branch") or "").strip()
    if dev:
        return dev
    main = (project.get("main_branch") or "").strip()
    if main:
        return main
    gh_headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
    }
    resp = requests.get(f"https://api.github.com/repos/{github_repo}", headers=gh_headers)
    if resp.ok:
        return resp.json().get("default_branch", "main")
    return "main"


KIND_PREFIX = {"feature": "Ftr", "bugfix": "Fix", "hotfix": "Fix", "enhancement": "Eta"}
KIND_MAP = {"bug": "bugfix", "feature": "feature", "enhancement": "enhancement", "hotfix": "hotfix"}


def classify_kind(task, client):
    for tag in (task.get("tags") or []):
        name = tag if isinstance(tag, str) else tag.get("name", "")
        if name in KIND_MAP:
            return KIND_MAP[name]
    msg = client.messages.create(
        model=MODEL,
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": (
                f"Task title: {task['title']}\n"
                f"Description: {task['description']}\n\n"
                "Reply with exactly one word — the git branch kind: "
                "feature, bugfix, hotfix, or enhancement."
            ),
        }],
    )
    word = msg.content[0].text.strip().lower()
    return word if word in ("feature", "bugfix", "hotfix", "enhancement") else "feature"


def _ask_claude_for_slug(client, title):
    msg = client.messages.create(
        model=MODEL,
        max_tokens=30,
        messages=[{
            "role": "user",
            "content": (
                f"Convert this task title to a short English slug suitable for a git branch name.\n"
                f"Rules:\n"
                f"- Use only lowercase ASCII letters, digits, and hyphens\n"
                f"- Maximum 40 characters\n"
                f"- No leading or trailing hyphens\n"
                f"- Capture the meaning concisely\n\n"
                f"Task title: {title}\n\n"
                f"Reply with ONLY the slug, nothing else."
            ),
        }],
    )
    raw = msg.content[0].text.strip().lower()
    slug = re.sub(r"[^a-z0-9-]", "-", raw)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:40] or "task"


def make_branch_name(kind, task_id, title, client):
    try:
        title.encode("ascii")
        is_ascii = True
    except UnicodeEncodeError:
        is_ascii = False

    if is_ascii:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        slug = slug[:40] or "task"
    else:
        slug = _ask_claude_for_slug(client, title)

    return f"{kind}/#{task_id}_{slug}"


def make_commit_message(kind, summary, task_id, details=None):
    prefix = KIND_PREFIX.get(kind, "Ftr")
    first = f"{prefix}: {summary} #{task_id}"[:50]
    lines = [first, ""]
    if details:
        for d in details:
            lines.append(f"- {d[:78]}")
    lines += ["", f"Task: {task_id}"]
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# PR helpers
# ---------------------------------------------------------------------------

def create_pr(github_repo, branch, task_id, title, kind, project, subtask_lines=None):
    prefix = KIND_PREFIX.get(kind, "Ftr")
    base = resolve_base_branch(project, github_repo)
    body_parts = []
    if subtask_lines:
        body_parts.append(subtask_lines)
    body_parts.append(f"Task: {task_id}")
    pr_resp = requests.post(
        f"https://api.github.com/repos/{github_repo}/pulls",
        headers={
            "Authorization": f"token {GITHUB_PAT}",
            "Accept": "application/vnd.github.v3+json",
        },
        json={
            "title": f"{prefix}: {title[:60]} #{task_id}",
            "head": branch,
            "base": base,
            "body": "\n\n".join(body_parts),
        },
    )
    if pr_resp.status_code == 201:
        pr_data = pr_resp.json()
        pr_url = pr_data["html_url"]
        pr_number = pr_data["number"]
        print(f"[agent] PR created: {pr_url}")
        task_data = api_get(f"task_app/tasks/{task_id}/")
        existing_desc = (task_data.get("description") or "").strip()
        pr_link = f"[PR #{pr_number}]({pr_url})"
        new_desc = f"{existing_desc}\n\n{pr_link}" if existing_desc else pr_link
        api_patch(f"task_app/tasks/{task_id}/", {"description": new_desc})
        print(f"[agent] Added PR link to task #{task_id} description.")
        return pr_data
    else:
        print(f"[agent] PR creation failed: {pr_resp.status_code} {pr_resp.text}", file=sys.stderr)
        return None


def handle_last_subtask(parent_task, all_sibling_ids, github_repo, branch, kind, project, author_id):
    parent_id = parent_task["id"]
    siblings = [api_get(f"task_app/tasks/{sid}/") for sid in all_sibling_ids]
    if not all(s["status"] == 4 for s in siblings):
        print(f"[agent] Siblings not all reviewed yet — no parent PR.")
        return

    sibling_lines = "\n".join(f"- #{s['id']}: {s['title']}" for s in siblings)
    subtask_summary = f"## 対応内容\n\n{sibling_lines}\n- #{TASK_ID}: (current subtask)"

    existing_desc = (parent_task.get("description") or "").strip()
    new_desc = f"{existing_desc}\n\n---\n\n{subtask_summary}" if existing_desc else subtask_summary

    api_patch(f"task_app/tasks/{parent_id}/", {"description": new_desc, "status": 4})
    print(f"[agent] Updated parent task #{parent_id} description and set to review.")

    pr_data = create_pr(github_repo, branch, parent_id, parent_task["title"], kind, project,
                        subtask_lines=subtask_summary)
    if pr_data:
        post_comment(parent_id, author_id, "対応が完了しました。")

# ---------------------------------------------------------------------------
# AgentCtx — shared state for one agent run
# ---------------------------------------------------------------------------

class AgentCtx:
    def __init__(self, client, github_repo, github_remote, project, branch, kind, workdir, automation_user_id):
        self.client = client
        self.github_repo = github_repo
        self.github_remote = github_remote
        self.project = project
        self.branch = branch
        self.kind = kind
        self.workdir = workdir
        self.automation_user_id = automation_user_id

# ---------------------------------------------------------------------------
# Core implementation step
# ---------------------------------------------------------------------------

def implement_task(task_id, ctx):
    """Ask Claude to implement a task, apply changes, test, commit, push.

    Updates the task status to レビュー (4) and posts a completion comment.
    Returns (task dict, commit_sha).
    Raises RuntimeError on failure (no files changed, tests fail, etc.).
    """
    task = api_get(f"task_app/tasks/{task_id}/")

    # Read codebase context
    context_files = []
    for root, dirs, files in os.walk(ctx.workdir):
        dirs[:] = [d for d in dirs if d not in {".git", "venv", "__pycache__", ".venv", "node_modules"}]
        for f in files:
            if f.endswith((".py", ".tf", ".md", ".lark")) and "migrations" not in root:
                path = os.path.join(root, f)
                rel = os.path.relpath(path, ctx.workdir)
                try:
                    content = open(path).read()
                    context_files.append(f"### {rel}\n```\n{content}\n```")
                except Exception:
                    pass
    context = "\n\n".join(context_files[:60])

    # Fetch task comments
    comments_resp = requests.get(
        f"{TASK_API_URL}/task_app/comments/",
        headers=api_headers,
        params={"task": task_id},
    )
    comments = comments_resp.json() if comments_resp.ok else []
    comments_text = "\n".join(
        f"[Comment #{c['id']}] {c['description']}" for c in comments
    ) if comments else "(no comments)"

    # Ask Claude
    prompt = (
        f"You are an expert Django developer working on the task-management project.\n\n"
        f"Task #{task_id}: {task['title']}\n"
        f"Description:\n{task['description']}\n\n"
        f"Comments on this task:\n{comments_text}\n\n"
        f"CLAUDE.md workflow is in the repo. Follow it.\n\n"
        f"Here is the relevant codebase:\n{context}\n\n"
        f"Provide the complete content of each file you need to create or modify. "
        f"Format each file as:\n"
        f"FILE: <relative/path/to/file>\n```\n<content>\n```\n\n"
        f"Only output FILE blocks. No explanations."
    )

    print(f"[agent] Calling Claude for task #{task_id}...")
    response = ctx.client.messages.create(
        model=MODEL,
        max_tokens=8096,
        messages=[{"role": "user", "content": prompt}],
    )
    implementation = response.content[0].text

    # Apply changes
    file_pattern = re.compile(r"FILE:\s*(\S+)\n```(?:\w*)\n(.*?)```", re.DOTALL)
    changed_files = []
    for match in file_pattern.finditer(implementation):
        rel_path, content = match.group(1).strip("`"), match.group(2)
        abs_path = os.path.join(ctx.workdir, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w") as fh:
            fh.write(content)
        changed_files.append(rel_path)
        print(f"[agent] Wrote {rel_path}")

    if not changed_files:
        raise RuntimeError(
            "No files were changed. The agent could not determine what to implement."
        )

    # Run tests
    django_dir = os.path.join(ctx.workdir, "django-app")
    if os.path.isdir(django_dir):
        run(["pip", "install", "-q", "-r", "requirements.txt"], cwd=django_dir, check=False)
        test_result = run(
            ["python", "manage.py", "test", "task_app", "event_app", "--verbosity=1"],
            cwd=django_dir,
            check=False,
            env={**os.environ, "DJANGO_SETTINGS_MODULE": "task_management.test_settings"},
        )
        if test_result.returncode != 0:
            raise RuntimeError(
                f"Tests failed. The agent could not complete the implementation.\n\n"
                f"```\n{test_result.stdout[-2000:]}\n{test_result.stderr[-1000:]}\n```"
            )
        print("[agent] Tests passed.")
    else:
        print("[agent] No django-app/ directory — skipping tests.")

    # Commit
    env_patch = {**os.environ, "DJANGO_SETTINGS_MODULE": "task_management.test_settings"}
    git(["add", "-A"], ctx.workdir)
    summary = task["title"][:44]
    commit_msg = make_commit_message(ctx.kind, summary, task_id)
    subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=ctx.workdir,
        env={**env_patch, "TASK_URL": f"{TASK_API_URL}/task_app/tasks"},
        check=True,
    )

    commit_sha = git(["rev-parse", "HEAD"], ctx.workdir).stdout.strip()

    # Push
    git(["push", "-u", "origin", ctx.branch], ctx.workdir)

    # Update task to レビュー, restore assignee
    review_patch = {"status": 4}
    if task.get("reporter"):
        review_patch["assignee"] = task["reporter"]
    api_patch(f"task_app/tasks/{task_id}/", review_patch)
    print(f"[agent] Task #{task_id} marked as review.")

    post_commit_comment(task_id, commit_sha, ctx.github_repo, ctx.automation_user_id)
    post_comment(task_id, ctx.automation_user_id, "対応が完了しました。")

    return task, commit_sha

# ---------------------------------------------------------------------------
# Script-callable functions
# ---------------------------------------------------------------------------

def _script_run_agent(task_id, ctx):
    """run_agent() callable from agent scripts."""
    implement_task(task_id, ctx)


def _script_create_pr(task_id, ctx, **kwargs):
    """create_pr() callable from agent scripts."""
    task = api_get(f"task_app/tasks/{task_id}/")
    create_pr(
        ctx.github_repo, ctx.branch, task_id, task["title"], ctx.kind, ctx.project,
        subtask_lines=kwargs.get("subtask_lines"),
    )


def _script_add_subtask(title, parent_task, ctx, **kwargs):
    """add_subtask() callable from agent scripts. Returns the new subtask ID."""
    result = api_post("task_app/tasks/", {
        "title": title,
        "project": kwargs.get("project", parent_task["project"]),
        "parent": kwargs.get("parent", parent_task["id"]),
        "event": kwargs.get("event", parent_task.get("event")),
        "assignee": ctx.automation_user_id,
        "status": 1,
    })
    subtask_id = result["id"]
    print(f"[agent] Created subtask #{subtask_id}: {title}")
    return subtask_id

# ---------------------------------------------------------------------------
# Agent script executor
# ---------------------------------------------------------------------------

_SAFE_BUILTINS = {
    "print": print,
    "range": range,
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "enumerate": enumerate,
    "zip": zip,
    "True": True,
    "False": False,
    "None": None,
}


def execute_agent_script(script_code, task_id, task, project, ctx):
    """Parse (via ast) and execute the project's agent script.

    The script runs with task_id, task, project, and three callable functions
    in its namespace: run_agent(), create_pr(), add_subtask().
    """
    try:
        tree = ast.parse(script_code, mode="exec")
    except SyntaxError as e:
        raise ValueError(f"Agent script syntax error: {e}")

    namespace = {
        "__builtins__": _SAFE_BUILTINS,
        "task_id": task_id,
        "task": task,
        "project": project,
        "run_agent": lambda tid=None: _script_run_agent(
            tid if tid is not None else task_id, ctx
        ),
        "create_pr": lambda tid=None, **kw: _script_create_pr(
            tid if tid is not None else task_id, ctx, **kw
        ),
        "add_subtask": lambda title, **kw: _script_add_subtask(
            title, task, ctx, **kw
        ),
    }

    exec(compile(tree, "<agent_script>", "exec"), namespace)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # 1. Fetch task
    task = api_get(f"task_app/tasks/{TASK_ID}/")
    print(f"[agent] Task #{TASK_ID}: {task['title']}")

    # 2. Resolve git remote from project's git_url
    project = api_get(f"task_app/projects/{task['project']}/")
    git_url = (project.get("git_url") or "").rstrip("/").removesuffix(".git")
    if not git_url:
        print("[agent] Project has no git_url set.", file=sys.stderr)
        sys.exit(1)
    parsed = urlparse(git_url)
    github_repo = parsed.path.lstrip("/")
    github_remote = f"https://{GITHUB_PAT}@{parsed.netloc}{parsed.path}.git"
    print(f"[agent] Repo: {github_repo}")

    # 3. Update status -> 着手済み
    api_patch(f"task_app/tasks/{TASK_ID}/", {"status": 2})

    # 4. Determine branch — subtasks share the parent's branch
    parent_task = None
    sibling_ids = []
    if task.get("parent"):
        parent_task = api_get(f"task_app/tasks/{task['parent']}/")
        kind = classify_kind(parent_task, client)
        branch = make_branch_name(kind, parent_task["id"], parent_task["title"], client)

        all_tasks = requests.get(f"{TASK_API_URL}/task_app/tasks/", headers=api_headers).json()
        sibling_ids = [
            t["id"] for t in all_tasks
            if t.get("parent") == parent_task["id"] and t["id"] != TASK_ID
        ]
    else:
        kind = classify_kind(task, client)
        branch = make_branch_name(kind, TASK_ID, task["title"], client)
    print(f"[agent] Branch: {branch}")

    automation_user = task.get("assignee")

    with tempfile.TemporaryDirectory() as workdir:
        # 5. Clone repo; checkout branch (create if needed)
        run(["git", "clone", github_remote, workdir])
        git(["config", "user.email", "claude-agent@example.com"], workdir)
        git(["config", "user.name", "Claude Agent"], workdir)
        if git(["checkout", branch], workdir, check=False).returncode != 0:
            git(["checkout", "-b", branch], workdir)

        ctx = AgentCtx(
            client=client,
            github_repo=github_repo,
            github_remote=github_remote,
            project=project,
            branch=branch,
            kind=kind,
            workdir=workdir,
            automation_user_id=automation_user,
        )

        agent_script = (project.get("agent") or "").strip()

        if agent_script:
            # Dynamic path: execute project-defined agent script
            print("[agent] Using project agent script.")
            try:
                execute_agent_script(agent_script, TASK_ID, task, project, ctx)
            except Exception as e:
                post_error_comment(task, str(e))
                sys.exit(1)
        else:
            # Default path: implement task then create PR
            try:
                implement_task(TASK_ID, ctx)
            except RuntimeError as e:
                post_error_comment(task, str(e))
                sys.exit(1)

            if parent_task:
                handle_last_subtask(
                    parent_task, sibling_ids, github_repo, branch, kind, project, automation_user
                )
            else:
                create_pr(github_repo, branch, TASK_ID, task["title"], kind, project)


if __name__ == "__main__":
    main()
