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
GITHUB_REPO = os.environ.get("GITHUB_REPO", "tombee-studio/task_management_tool")
GITHUB_REMOTE = f"https://{GITHUB_PAT}@github.com/{GITHUB_REPO}.git"
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


def run(cmd, cwd=None, check=True):
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


def git(args, cwd):
    return run(["git"] + args, cwd=cwd)


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
            lines.append(f"- {d[:48]}")
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

    # 2. Update status -> 着手済み
    api_patch(f"task_app/tasks/{TASK_ID}/", {"status": 2})

    # 3. Classify kind
    kind = classify_kind(task, client)
    branch = re.sub(r"[^a-z0-9_]", "_", f"{kind}/#{TASK_ID}_{task['title'].lower()}")[:60]
    print(f"[agent] Branch: {branch}")

    with tempfile.TemporaryDirectory() as workdir:
        # 4. Clone repo
        run(["git", "clone", GITHUB_REMOTE, workdir])
        git(["config", "user.email", "claude-agent@example.com"], workdir)
        git(["config", "user.name", "Claude Agent"], workdir)
        git(["checkout", "-b", branch], workdir)

        # 5. Read codebase context
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

        # 6. Ask Claude to implement
        prompt = (
            f"You are an expert Django developer working on the task-management project.\n\n"
            f"Task #{TASK_ID}: {task['title']}\n"
            f"Description:\n{task['description']}\n\n"
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

        # 7. Apply changes
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
            return

        # 8. Run tests
        django_dir = os.path.join(workdir, "django-app")
        test_result = run(
            ["python", "manage.py", "test", "task_app", "event_app", "--verbosity=1"],
            cwd=django_dir,
            check=False,
        )
        if test_result.returncode != 0:
            print("[agent] Tests failed:\n", test_result.stdout, test_result.stderr, file=sys.stderr)
            api_patch(f"task_app/tasks/{TASK_ID}/", {"progress_summary": "Tests failed"})
            sys.exit(1)
        print("[agent] Tests passed.")

        # 9. Commit
        env_patch = {**os.environ, "DJANGO_SETTINGS_MODULE": "task_management.test_settings"}
        git(["add", "-A"], workdir)
        summary = task["title"][:44]
        commit_msg = make_commit_message(kind, summary, TASK_ID)
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=workdir,
            env={**env_patch, "TASK_URL": f"{TASK_API_URL}/task_app/tasks"},
            check=True,
        )

        # 10. Push branch
        git(["push", "origin", branch], workdir)

        # 11. Merge to develop via GitHub API
        merge_resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/merges",
            headers={
                "Authorization": f"token {GITHUB_PAT}",
                "Accept": "application/vnd.github.v3+json",
            },
            json={"base": "develop", "head": branch, "commit_message": f"Merge {branch} into develop"},
        )
        if merge_resp.status_code in (201, 204):
            print(f"[agent] Merged {branch} -> develop")
        else:
            print(f"[agent] Merge failed: {merge_resp.status_code} {merge_resp.text}", file=sys.stderr)

        # 12. Update task status to merged
        api_patch(f"task_app/tasks/{TASK_ID}/", {"status": TASK_STATUS_MERGE_ID})
        print(f"[agent] Task #{TASK_ID} marked as merged.")


if __name__ == "__main__":
    main()
