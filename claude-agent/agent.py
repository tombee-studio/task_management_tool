"""Claude automation agent.

Reads TASK_ID from the environment, fetches the task from the API,
and drives the agent using the project's `agent` script field.

If Project.agent is set, its content is executed as a Python script
(validated via ast.parse).  The script receives:

  ctx       -- AgentCtx instance with all agent operations
  task_id   -- int, the current task ID
  SMALL / MIDDLE / LARGE -- modification level constants

If Project.agent is empty the default pipeline runs.
"""
import ast
import os
import sys

import requests

from agent_ctx import AgentCtx, SMALL, MIDDLE, LARGE

# ---------------------------------------------------------------------------
# Config from environment
# ---------------------------------------------------------------------------

TASK_ID = int(os.environ["TASK_ID"])
TASK_API_URL = os.environ["TASK_API_URL"].rstrip("/")
TASK_API_KEY = os.environ["TASK_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GITHUB_PAT = os.environ["GITHUB_PAT"]
MODEL = "claude-sonnet-4-6"

_API_HEADERS = {"X-API-Key": TASK_API_KEY, "Content-Type": "application/json"}

# ---------------------------------------------------------------------------
# Default pipeline (used when Project.agent is not set)
# ---------------------------------------------------------------------------

DEFAULT_AGENT_SCRIPT = """\
ctx.clone_git_url()
task = ctx.get_task()
kinds = ctx.get_kinds()
ctx.decide_strategy(task, kinds)
ctx.branch(task)
ctx.push(task)
ctx.gh_create_pr(task)
ctx.change_assignee(ctx.get_assignee())
"""

# ---------------------------------------------------------------------------
# Script executor
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


def execute_agent_script(script_code, ctx):
    """Parse (via ast) and execute an agent script with ctx in scope."""
    try:
        tree = ast.parse(script_code, mode="exec")
    except SyntaxError as e:
        raise ValueError(f"Agent script syntax error: {e}")

    namespace = {
        "__builtins__": _SAFE_BUILTINS,
        "ctx": ctx,
        "task_id": TASK_ID,
        "SMALL": SMALL,
        "MIDDLE": MIDDLE,
        "LARGE": LARGE,
    }

    exec(compile(tree, "<agent_script>", "exec"), namespace)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Fetch task and project
    task_resp = requests.get(
        f"{TASK_API_URL}/task_app/tasks/{TASK_ID}/", headers=_API_HEADERS
    )
    task_resp.raise_for_status()
    task = task_resp.json()
    print(f"[agent] Task #{TASK_ID}: {task['title']}")

    project_resp = requests.get(
        f"{TASK_API_URL}/task_app/projects/{task['project']}/", headers=_API_HEADERS
    )
    project_resp.raise_for_status()
    project = project_resp.json()

    # Update status to 着手済み (2)
    requests.patch(
        f"{TASK_API_URL}/task_app/tasks/{TASK_ID}/",
        headers=_API_HEADERS,
        json={"status": 2},
    )

    ctx = AgentCtx(
        task_id=TASK_ID,
        api_url=TASK_API_URL,
        api_key=TASK_API_KEY,
        github_pat=GITHUB_PAT,
        anthropic_api_key=ANTHROPIC_API_KEY,
        model=MODEL,
    )

    agent_script = (project.get("agent") or "").strip()
    if agent_script:
        print("[agent] Using project agent script.")
        script = agent_script
    else:
        print("[agent] Using default agent script.")
        script = DEFAULT_AGENT_SCRIPT

    try:
        execute_agent_script(script, ctx)
    except Exception as e:
        _post_error(task, str(e))
        print(f"[agent] Error: {e}", file=sys.stderr)
        sys.exit(1)


def _post_error(task, error_text):
    try:
        requests.post(
            f"{TASK_API_URL}/task_app/comments/",
            headers=_API_HEADERS,
            json={
                "author": task["assignee"],
                "description": f"[Automation Error]\n\n{error_text}",
                "task": task["id"],
            },
        )
    except Exception:
        pass
    if task.get("reporter"):
        try:
            requests.patch(
                f"{TASK_API_URL}/task_app/tasks/{task['id']}/",
                headers=_API_HEADERS,
                json={"assignee": task["reporter"]},
            )
        except Exception:
            pass


if __name__ == "__main__":
    main()
