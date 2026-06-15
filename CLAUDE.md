# CLAUDE.md

This file documents the standard workflow for implementing a task in this project.

## Automation user workflow

The system has a special Django user **Automation** (`username='Automation'`, `is_active=False`).

**Trigger**: When a task's `assignee` is changed **to** Automation (not on task creation), a signal
sends the task to an SQS queue, which launches the `claude-agent` ECS task automatically.

**On completion**: After the agent commits and pushes, it sets the task status to `レビュー` (4)
**and** restores `assignee` to the task's `reporter` field (the user who originally created the task).

**reporter field**: The `reporter` FK on `Task` is set to `request.user` when a task is created via
the web UI. It is exposed in the REST API (`TaskSerializer`) as a nullable field.

## Workflow

### 1. Receive task

Tasks arrive with a task ID (e.g., `#128`). Confirm the scope before starting.

Set status to 着手済み (status=2) when starting work:

```bash
eval "$(direnv export bash)"
curl -s -X PATCH \
  "${TOOL_API_URL}task_app/tasks/<task_id>/" \
  -H "X-API-Key: ${TOOL_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"status": 2}'
```

### 2. Create a feature branch

Create **one** feature branch for the received task (★). Subtasks never get their own branch.

Branch naming convention: `<kind>/#<task_id>_<short_description>`

| kind | use case |
|------|----------|
| `feature` | new functionality |
| `bugfix` | bug fix |
| `hotfix` | urgent production fix |
| `enhancement` | improvement to existing feature |

```bash
git checkout develop
git checkout -b feature/#<task_id>_<desc>
```

### 3. Assess scope and create subtasks if needed

**Small task** (no subtask division needed) → skip this step and proceed to implementation.

**Large task** (needs subtask division):

1. Decide subtasks upfront and create them all at once via the API:
   - `parent`: set to the received task (★)
   - `event`: same as the received task (★)
2. Proceed to implementation within the single feature branch created in step 2.

```bash
# Create a subtask
eval "$(direnv export bash)"
curl -s -X POST "${TOOL_API_URL}task_app/tasks/" \
  -H "X-API-Key: ${TOOL_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"title": "...", "project": <project_id>, "assignee": <user_id>,
       "status": 1, "parent": <parent_task_id>, "event": <event_id>}'
```

### 4. Implement changes

Work inside `django-app/`. Edit models, views, forms, DSL, templates, etc.

While implementing, if you discover bugs, improvements, or technical debt **outside the scope of the current task**, file them as new tasks via the API:

```bash
eval "$(direnv export bash)"
curl -s -X POST "${TOOL_API_URL}task_app/tasks/" \
  -H "X-API-Key: ${TOOL_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"title": "...", "description": "...", "project": <project_id>,
       "assignee": <user_id>, "status": 1, "event": <event_id>}'
```

### 5. Run tests

Always use `task_management.test_settings` when running tests:

```bash
cd django-app
DJANGO_SETTINGS_MODULE=task_management.test_settings python manage.py test task_app event_app
```

Or via Make (runs the same command):

```bash
make test
```

All tests must pass before committing.

### 6. Commit

The `commit-msg` hook enforces the following format (all lines ASCII only):

```
<kind>: <Summary starting with uppercase> #<task_id>

- Detail line (50 chars max)
- Detail line (50 chars max)

Task: <task_id>
```

Rules:
- `kind`: `Ftr` (feature) / `Fix` (bug fix) / `Eta` (eta/enhancement)
- First line: ASCII only, 50 characters or fewer
- Blank line after the first line
- Detail lines: ASCII only, 50 characters or fewer each (optional)
- Blank line immediately before `Task:`
- Last line: `Task: <task_id>` — the hook rewrites this to a Markdown link automatically

**Which task ID to use in the commit:**

| Situation | Task ID in commit |
|-----------|------------------|
| Small task (no subtasks) | ★ (received task) |
| Large task — commit implements a subtask | Subtask ID |

`TASK_URL` must be set (loaded automatically via `direnv allow`):

```bash
eval "$(direnv export bash)"
git add <files>
git commit -m "$(cat <<'EOF'
Ftr: Add PARENT DSL command #128

- Implement execute_parent() and dispatch
- Add PARENT help text to forms

Task: 128
EOF
)"
```

### 7. After each subtask commit — update subtask status

After committing a subtask's changes, set the **subtask** status to レビュー (status=4):

```bash
eval "$(direnv export bash)"
curl -s -X PATCH \
  "${TOOL_API_URL}task_app/tasks/<subtask_id>/" \
  -H "X-API-Key: ${TOOL_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"status": 4}'
```

マージ済み (status=12) への更新は GitHub Actions が develop へのマージ時に自動で行うため、手動での変更は不要。

### 8. Push and create PR

```bash
git push -u origin <branch>
```

The pre-push hook runs all tests automatically before pushing.

Then create a PR targeting `develop`, including `Task: <task_id>` in the PR body:

```bash
eval "$(direnv export bash)"
gh pr create \
  --base develop \
  --title "<kind>: <Summary> #<task_id>" \
  --body "$(cat <<'EOF'
- Detail line

Task: <task_id>
EOF
)"
```

### 9. Add PR link to task description

After creating the PR, append a Markdown link to the task description:

```bash
eval "$(direnv export bash)"
EXISTING=$(curl -s "${TOOL_API_URL}task_app/tasks/<task_id>/" \
  -H "X-API-Key: ${TOOL_API_KEY}" | python3 -c \
  "import sys,json; print(json.load(sys.stdin).get('description',''))")

curl -s -X PATCH "${TOOL_API_URL}task_app/tasks/<task_id>/" \
  -H "X-API-Key: ${TOOL_API_KEY}" \
  -H "Content-Type: application/json" \
  --data-binary "$(python3 -c "
import json, sys
desc = sys.stdin.read()
desc += '\n\n[PR #<pr_number>](https://github.com/<owner>/<repo>/pull/<pr_number>)'
print(json.dumps({'description': desc}))
" <<< "$EXISTING")"
```

## API Reference

- **API docs**: https://8hzryl7735.execute-api.ap-northeast-1.amazonaws.com/prd/api/docs/
- **Base URL**: defined in `.envrc` as `TOOL_API_URL`
- **Auth**: `X-API-Key` header using `TOOL_API_KEY` from `.envrc`

## Quick reference

```
# -- Small task --
# 1. Set status to 着手済み
curl -s -X PATCH "${TOOL_API_URL}task_app/tasks/<id>/" \
  -H "X-API-Key: ${TOOL_API_KEY}" -H "Content-Type: application/json" \
  -d '{"status": 2}'

# 2. Branch
git checkout -b feature/#<id>_<desc>

# 3. Implement & test (file any discovered issues as new tasks)
make test

# 4. Commit (use ★ task ID)
eval "$(direnv export bash)"
git add <files>
git commit -m "Ftr: <summary> #<id>\n\n- <detail>\n\nTask: <id>"

# 5. Push and create PR (body must include Task: <id>)
git push -u origin <branch>
gh pr create --base develop --title "..." --body "...\n\nTask: <id>"

# 6. Add PR link to task description
curl -s -X PATCH "${TOOL_API_URL}task_app/tasks/<id>/" \
  -H "X-API-Key: ${TOOL_API_KEY}" -H "Content-Type: application/json" \
  -d '{"description": "<existing>\n\nPR: https://github.com/<owner>/<repo>/pull/<n>"}'

# 6. Create PR (include Task: <id> in body)
gh pr create --base develop --title "..." --body "...\n\nTask: <id>"

# 7. Add PR link to task description (Markdown format)
curl -s -X PATCH "${TOOL_API_URL}task_app/tasks/<id>/" \
  -H "X-API-Key: ${TOOL_API_KEY}" -H "Content-Type: application/json" \
  -d '{"description": "<existing>\n\n[PR #<n>](https://github.com/<owner>/<repo>/pull/<n>)"}'


# -- Large task (with subtasks) --
# 1. Set status to 着手済み
# 2. Create subtasks via API (parent=★, event=★)
# 3. Branch (one branch for ★, no branch per subtask)
git checkout -b feature/#<★id>_<desc>

# 4. For each subtask: implement, test, commit with SUBTASK ID
git commit -m "Ftr: <summary> #<subtask_id>\n\n...\n\nTask: <subtask_id>"

# 5. After each subtask commit: set subtask status to レビュー
curl -s -X PATCH "${TOOL_API_URL}task_app/tasks/<subtask_id>/" \
  -H "X-API-Key: ${TOOL_API_KEY}" -H "Content-Type: application/json" \
  -d '{"status": 4}'

# 6. Push and create PR with PARENT task ID in body
git push -u origin <branch>

# 7. Create PR with Task: <★id> in body
gh pr create --base develop --title "..." --body "...\n\nTask: <★id>"

# 8. Add PR link to parent task description (Markdown format)
curl -s -X PATCH "${TOOL_API_URL}task_app/tasks/<★id>/" \
  -H "X-API-Key: ${TOOL_API_KEY}" -H "Content-Type: application/json" \
  -d '{"description": "<existing>\n\n[PR #<n>](https://github.com/<owner>/<repo>/pull/<n>)"}'
```
