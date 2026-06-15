"""Claude automation agent.

Reads TASK_ID from the environment, fetches the task from the API,
uses Claude to implement the required change, runs tests, commits,
pushes, merges to develop, and updates the task status.
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
# Helpers
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


def get_automation_user_id():
    """Look up the Automation user ID via the API. Returns None if not found."""
    try:
        resp = requests.get(
            f"{TASK_API_URL}/task_app/tasks/",
            headers=api_headers,
        )
        # Use a direct user lookup approach — search for Automation in task assignees
        # Instead, look up via user preferences or tasks assigned to Automation
        # We'll use a dedicated approach: list users if available, otherwise skip
        pass
    except Exception:
        pass

    # Try to find Automation user by checking tasks assigned to it,
    # or fall back to None (assignee will not be set)
    try:
        # Use the tasks API to find any task assigned to Automation
        # This is a workaround since there's no direct users list endpoint
        tasks_resp = requests.get(
            f"{TASK_API_URL}/task_app/tasks/",
            headers=api_headers,
        )
        if tasks_resp.ok:
            tasks = tasks_resp.json()
            # Find a task where assignee corresponds to Automation
            # We can't determine this without a users endpoint
            pass
    except Exception:
        pass

    return None


def _get_automation_user_id_from_task(task):
    """
    Attempt to resolve the Automation user ID.

    Strategy:
    1. If the current task's assignee is Automation (i.e. this agent was triggered
       by assigning the task to Automation), use that assignee ID.
    2. Otherwise return None and let the caller decide.
    """
    # The agent is triggered when a task is assigned to Automation.
    # So task["assignee"] IS the Automation user's ID at the time the agent runs.
    return task.get("assignee")


def post_comment(task_id, author_id, text):
    """Post a comment on a task."""
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
    """Post commit link as a comment on the task."""
    commit_url = f"https://github.com/{github_repo}/commit/{commit_sha}"
    post_comment(task_id, author_id, f"対応コミット: [{commit_sha[:8]}]({commit_url})")


def post_error_comment(task, error_text):
    """Post an error comment and restore assignee to reporter."""
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


def file_discovered_issues(client, task, context):
    """Ask Claude if it found any out-of-scope issues and file them as new tasks.

    Discovered issues are filed as independent tasks (not subtasks) with
    assignee set to the Automation user so they can be auto-processed.
    The parent field is intentionally omitted — these are separate work items
    unrelated to the current task's scope.
    """
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": (
                f"You just implemented task #{task['id']}: {task['title']}.\n"
                f"While reviewing this codebase, did you notice any bugs, improvements, "
                f"or technical debt that are OUT OF SCOPE for this task?\n\n"
                f"Codebase context:\n{context[:4000]}\n\n"
                f"For each issue found, respond with:\n"
                f"ISSUE: <short title under 100 chars>\n"
                f"DETAIL: <description>\n\n"
                f"If none found, respond with exactly: NONE"
            ),
        }],
    )
    text = resp.content[0].text.strip()
    if text.upper() == "NONE":
        return

    # The Automation user is the current assignee of the task (the agent was
    # triggered by assigning the task to Automation).
    automation_user_id = _get_automation_user_id_from_task(task)

    pattern = re.compile(r"ISSUE:\s*(.+?)\nDETAIL:\s*(.+?)(?=\nISSUE:|$)", re.DOTALL)
    for m in pattern.finditer(text):
        title = m.group(1).strip()[:100]
        detail = m.group(2).strip()
        # File as an independent task — NOT a subtask (no parent field).
        # Use Automation as assignee so these tasks can be picked up automatically.
        task_data = {
            "title": title,
            "description": detail,
            "project": task["project"],
            "status": 1,
        }
        if automation_user_id:
            task_data["assignee"] = automation_user_id
        if task.get("event"):
            task_data["event"] = task["event"]
        new_task = api_post("task_app/tasks/", task_data)
        print(f"[agent] Filed issue task #{new_task['id']}: {title}")


def resolve_base_branch(project, github_repo):
    """Return the branch PRs should target.

    Priority: dev_branch → main_branch → GitHub API default_branch.
    """
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
        # Add PR link (Markdown) to task description
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
    """When all sibling subtasks are in レビュー, update parent description and create PR."""
    parent_id = parent_task["id"]

    # Fetch current status of all siblings (excluding current task, already set to レビュー)
    siblings = [api_get(f"task_app/tasks/{sid}/") for sid in all_sibling_ids]
    if not all(s["status"] == 4 for s in siblings):
        print(f"[agent] Siblings not all reviewed yet — no parent PR.")
        return

    # Build implementation summary from subtask titles
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


def run(cmd, cwd=None, check=True, env=None):
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True, env=env)


def git(args, cwd, check=True):
    return run(["git"] + args, cwd=cwd, check=check)


# ---------------------------------------------------------------------------
# Branch name helpers
# ---------------------------------------------------------------------------

def _ask_claude_for_slug(client, title):
    """Ask Claude to translate/summarize a task title into a short ASCII slug."""
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
    # Sanitize just in case Claude returns something unexpected
    slug = re.sub(r"[^a-z0-9-]", "-", raw)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:40] or "task"


def make_branch_name(kind, task_id, title, client):
    """Build a meaningful ASCII branch name from a task ID and title.

    If the title is already ASCII-only, use it directly (lowercased, spaces→hyphens).
    If it contains non-ASCII characters (e.g. Japanese), ask Claude for a translation slug.
    """
    # Check if the title is ASCII-only
    try:
        title.encode("ascii")
        is_ascii = True
    except UnicodeEncodeError:
        is_ascii = False

    if is_ascii:
        # Convert to lowercase slug: replace non-alphanumeric with hyphens
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        slug = slug[:40] or "task"
    else:
        slug = _ask_claude_for_slug(client, title)

    branch = f"{kind}/#{task_id}_{slug}"
    return branch


# ---------------------------------------------------------------------------
# Tag classification
# ---------------------------------------------------------------------------

KIND_MAP = {"bug": "bugfix", "feature": "feature", "enhancement": "enhancement", "hotfix": "hotfix"}

def classify_kind(task, client):
    """Ask Claude which branch kind fits the task."""
    tags = [t.get("name", "") for t in api_get(f"task_app/tasks/{task['id']}/")
            .get("tags", [])] if False else []
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


# ---------------------------------------------------------------------------
# Commit message
# ---------------------------------------------------------------------------

KIND_PREFIX = {"feature": "Ftr", "bugfix": "Fix", "hotfix": "Fix", "enhancement": "Eta"}

def make_commit_message(kind, summary, task_id, details=None):
    prefix = KIND_PREFIX.get(kind, "Ftr")
    first = f"{prefix}: {summary} #{task_id}"
    first = first[:50]
    lines = [first, ""]
    if details:
        for d in details:
            lines.append(f"- {d[:78]}")
    lines += ["", f"Task: {task_id}"]
    return "\n".join(lines)


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
    github_repo = parsed.path.lstrip("/")  # "owner/repo"
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
        commit_task_id = TASK_ID

        # Collect sibling subtask IDs (to check completion later)
        all_tasks = requests.get(f"{TASK_API_URL}/task_app/tasks/", headers=api_headers).json()
        sibling_ids = [
            t["id"] for t in all_tasks
            if t.get("parent") == parent_task["id"] and t["id"] != TASK_ID
        ]
    else:
        kind = classify_kind(task, client)
        branch = make_branch_name(kind, TASK_ID, task["title"], client)
        commit_task_id = TASK_ID
    print(f"[agent] Branch: {branch}")

    with tempfile.TemporaryDirectory() as workdir:
        # 5. Clone repo; checkout parent branch if it exists, else create it
        run(["git", "clone", github_remote, workdir])
        git(["config", "user.email", "claude-agent@example.com"], workdir)
        git(["config", "user.name", "Claude Agent"], workdir)
        if git(["checkout", branch], workdir, check=False).returncode != 0:
            git(["checkout", "-b", branch], workdir)

        # 6. Read codebase context
        context_files = []
        for root, dirs, files in os.walk(workdir):
            dirs[:] = [d for d in dirs if d not in {".git", "venv", "__pycache__", ".venv", "node_modules"}]
            for f in files:
                if f.endswith((".py", ".tf", ".md", ".lark")) and "migrations" not in root:
                    path = os.path.join(root, f)
                    rel = os.path.relpath(path, workdir)
                    try:
                        content = open(path).read()
                        context_files.append(f"### {rel}\n```\n{content}\n```")
                    except Exception:
                        pass

        context = "\n\n".join(context_files[:60])  # cap to avoid token overflow

        # 7a. Fetch task comments
        comments_resp = requests.get(
            f"{TASK_API_URL}/task_app/comments/",
            headers=api_headers,
            params={"task": TASK_ID},
        )
        comments = comments_resp.json() if comments_resp.ok else []
        comments_text = "\n".join(
            f"[Comment #{c['id']}] {c['description']}" for c in comments
        ) if comments else "(no comments)"

        # 7b. Ask Claude to implement
        prompt = (
            f"You are an expert Django developer working on the task-management project.\n\n"
            f"Task #{TASK_ID}: {task['title']}\n"
            f"Description:\n{task['description']}\n\n"
            f"Comments on this task:\n{comments_text}\n\n"
            f"CLAUDE.md workflow is in the repo. Follow it.\n\n"
            f"Here is the relevant codebase:\n{context}\n\n"
            f"Provide the complete content of each file you need to create or modify. "
            f"Format each file as:\n"
            f"FILE: <relative/path/to/file>\n```\n<content>\n```\n\n"
            f"Only output FILE blocks. No explanations."
        )

        print("[agent] Calling Claude for implementation...")
        response = client.messages.create(
            model=MODEL,
            max_tokens=8096,
            messages=[{"role": "user", "content": prompt}],
        )
        implementation = response.content[0].text

        # 8. Apply changes
        file_pattern = re.compile(r"FILE:\s*(\S+)\n```(?:\w*)\n(.*?)```", re.DOTALL)
        changed_files = []
        for match in file_pattern.finditer(implementation):
            rel_path, content = match.group(1), match.group(2)
            abs_path = os.path.join(workdir, rel_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w") as fh:
                fh.write(content)
            changed_files.append(rel_path)
            print(f"[agent] Wrote {rel_path}")

        if not changed_files:
            print("[agent] No files changed — nothing to commit.", file=sys.stderr)
            post_error_comment(task, "No files were changed. The agent could not determine what to implement.")
            return

        # 9. File discovered out-of-scope issues as new tasks
        file_discovered_issues(client, task, context)

        # 11. Run tests (Django-only; skip if no django-app directory)
        django_dir = os.path.join(workdir, "django-app")
        if os.path.isdir(django_dir):
            run(["pip", "install", "-q", "-r", "requirements.txt"], cwd=django_dir, check=False)
            test_result = run(
                ["python", "manage.py", "test", "task_app", "event_app", "--verbosity=1"],
                cwd=django_dir,
                check=False,
                env={**os.environ, "DJANGO_SETTINGS_MODULE": "task_management.test_settings"},
            )
            if test_result.returncode != 0:
                print("[agent] Tests failed:\n", test_result.stdout, test_result.stderr, file=sys.stderr)
                error_text = (
                    f"Tests failed. The agent could not complete the implementation.\n\n"
                    f"```\n{test_result.stdout[-2000:]}\n{test_result.stderr[-1000:]}\n```"
                )
                post_error_comment(task, error_text)
                sys.exit(1)
            print("[agent] Tests passed.")
        else:
            print("[agent] No django-app/ directory — skipping tests.")

        # 12. Commit (subtasks use their own ID; small tasks use their ID)
        env_patch = {**os.environ, "DJANGO_SETTINGS_MODULE": "task_management.test_settings"}
        git(["add", "-A"], workdir)
        summary = task["title"][:44]
        commit_msg = make_commit_message(kind, summary, commit_task_id)
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=workdir,
            env={**env_patch, "TASK_URL": f"{TASK_API_URL}/task_app/tasks"},
            check=True,
        )

        # Get commit SHA before push for comments
        commit_sha = git(["rev-parse", "HEAD"], workdir).stdout.strip()

        # 13. Push branch
        git(["push", "-u", "origin", branch], workdir)

        # 14. Update this task to レビュー and restore assignee to reporter
        review_patch = {"status": 4}
        if task.get("reporter"):
            review_patch["assignee"] = task["reporter"]
        api_patch(f"task_app/tasks/{TASK_ID}/", review_patch)
        print(f"[agent] Task #{TASK_ID} marked as review.")

        # 15. Post commit link and completion comment on current task
        automation_user = task["assignee"]
        post_commit_comment(TASK_ID, commit_sha, github_repo, automation_user)
        post_comment(TASK_ID, automation_user, "対応が完了しました。")

        # 16. PR creation — parent task PR after all subtasks done, else direct PR
        if parent_task:
            handle_last_subtask(parent_task, sibling_ids, github_repo, branch, kind, project, automation_user)
        else:
            create_pr(github_repo, branch, TASK_ID, task["title"], kind, project)


if __name__ == "__main__":
    main()
