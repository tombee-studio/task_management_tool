# CLAUDE.md

This file documents the standard workflow for implementing a task in this project.

## Workflow

### 1. Receive task

Tasks arrive with a task ID (e.g., `#128`). Confirm the scope before starting.

### 2. Create a feature branch

Branch naming convention: `<kind>/#<task_id>_<short_description>`

| kind | use case |
|------|----------|
| `feature` | new functionality |
| `bugfix` | bug fix |
| `hotfix` | urgent production fix |
| `enhancement` | improvement to existing feature |

Example:
```
git checkout -b feature/#128_add_parent_change_dsl
```

### 3. Implement changes

Work inside `django-app/`. Edit models, views, forms, DSL, templates, etc.

### 4. Run tests

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

### 5. Commit

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

### 6. Update task status

After committing (or after merging), update the task status in the task management tool via the API:

```bash
eval "$(direnv export bash)"
curl -s -X PATCH \
  "${TOOL_API_URL}task_app/tasks/<task_id>/" \
  -H "X-API-Key: ${TOOL_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"status\": ${TASK_STAUS_MERGE_ID}}"
```

- `TOOL_API_URL`, `TOOL_API_KEY`, `TASK_STAUS_MERGE_ID` are all defined in `.envrc`.
- `TASK_STAUS_MERGE_ID` is the status ID that represents "merged / done".

## Quick reference

```
# 1. Branch
git checkout -b feature/#<id>_<desc>

# 2. Implement & test
make test

# 3. Commit
eval "$(direnv export bash)"
git add <files>
git commit -m "Ftr: <summary> #<id>\n\n- <detail>\n\nTask: <id>"

# 4. Update task status
eval "$(direnv export bash)"
curl -s -X PATCH "${TOOL_API_URL}task_app/tasks/<id>/" \
  -H "X-API-Key: ${TOOL_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"status\": ${TASK_STAUS_MERGE_ID}}"
```
