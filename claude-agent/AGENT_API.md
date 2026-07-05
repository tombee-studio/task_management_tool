# Agent Script API リファレンス

このドキュメントは、`Project.agent`／`TaskType.agent` フィールドに保存される
**Agent Script**（Python）から利用できる API を調査・整理したものです。Agent Script は
`claude-agent/agent.py` の `execute_agent_script()` によって `ast.parse` 検証後に実行され、
`claude-agent/agent_ctx.py` の `AgentCtx` インスタンスを通じてすべての操作を行います。

- 対象コード: `claude-agent/agent.py` / `claude-agent/agent_ctx.py`
- 実行トリガー: タスクの `assignee` が Automation ユーザーに変更されたとき（CLAUDE.md 参照）
- `TaskType.agent` が空の場合は `DEFAULT_AGENT_SCRIPT` が実行されます。

---

## 1. 実行環境（スクリプトのスコープ）

`execute_agent_script(script_code, ctx)` は、以下の名前を namespace に注入したうえで
スクリプトを `exec` します。組み込み関数は `_SAFE_BUILTINS` に限定されています。

| 名前 | 種別 | 説明 |
|------|------|------|
| `ctx` | `AgentCtx` | エージェント操作の本体。すべての処理はこのオブジェクト経由で呼び出す。 |
| `task_id` | `int` | 現在処理しているタスクの ID（環境変数 `TASK_ID`）。 |
| `SMALL` | `int` (=1) | 改修規模の定数（小）。 |
| `MIDDLE` | `int` (=2) | 改修規模の定数（中）。 |
| `LARGE` | `int` (=3) | 改修規模の定数（大）。 |
| `run_agent` | callable | `ctx.run_agent` へのトップレベル別名。 |
| `create_pr` | callable | `ctx.gh_create_pr` へのトップレベル別名。 |
| `execute_dsl` | callable | `ctx.execute_dsl` へのトップレベル別名。 |

### 利用可能な組み込み関数（`_SAFE_BUILTINS`）

`print`, `range`, `len`, `str`, `int`, `float`, `bool`, `list`, `dict`, `tuple`,
`enumerate`, `zip`, `True`, `False`, `None`

> 注意: `import` やファイル I/O などは namespace に含まれないため使用できません。
> 構文エラーがある場合は `execute_agent_script` が `ValueError` を送出します。

---

## 2. データクラス

### `TaskKind`

タスクの種別を表す軽量クラス。

| メンバ | 型 | 説明 |
|--------|----|------|
| `name` | `str` | 種別名（例: `feature`, `bugfix`）。 |

### `TaskInfo`

`ctx.get_task()` が返すタスク情報。`_raw` に元の API レスポンス dict を保持します。

| 属性 | 型 | 説明 |
|------|----|------|
| `id` | `int` | タスク ID |
| `title` | `str` | タイトル |
| `description` | `str` | 説明 |
| `status` | `int` / `None` | ステータス ID |
| `assignee` | `int` / `None` | 担当者ユーザー ID |
| `reporter` | `int` / `None` | 起票者ユーザー ID |
| `parent` | `int` / `None` | 親タスク ID |
| `project` | `int` | プロジェクト ID |
| `event` | `int` / `None` | 紐づくイベント ID |
| `comments` | `list[dict]` | コメント一覧 |
| `kind` | `TaskKind` / `None` | タスク種別 |

### `Strategy`

`ctx.decide_strategy()` が返す実装方針。

| 属性 | 型 | 説明 |
|------|----|------|
| `approach` | `str` | 実装方針の説明 |
| `subtask_titles` | `list[str]` | 生成すべきサブタスクのタイトル（不要なら空リスト） |

---

## 3. `AgentCtx` メソッド一覧

引数 `task` は `TaskInfo` でも生の dict でも受け付けられるメソッドがあります。
CRUD 系メソッドで未指定のパラメータは、現タスクから `project`/`assignee`/`event` を
継承する既存思想を踏襲します（`create_*` を参照）。エンドポイントは REST API の
実パス（`task_app/tasks/`, `task_app/statuses/`, `task_app/comments/`,
`event_app/events/`, `task_app/dsl/execute/`）を使用します。

### 3.1 一般

| メソッド | 引数 | 戻り値 | 説明 |
|----------|------|--------|------|
| `get_kinds()` | なし | `list[TaskKind]` | プロジェクトのタスク種別一覧を取得。 |
| `clone_git_url()` | なし | `None` | プロジェクトの `git_url` を一時ディレクトリに clone。git 操作前に必須。`git_url` 未設定時は `RuntimeError`。 |
| `decide_strategy(task, kinds)` | `task`, `kinds` | `Strategy` | Claude に実装方針を計画させ、内部に保存して返す。 |
| `get_modification_level()` | なし | `int` (`SMALL`/`MIDDLE`/`LARGE`) | Claude に改修規模を判定させる。不明時は `MIDDLE`。 |
| `branch(task)` | `task` | `None` | タスクに応じた git ブランチを作成/切替。`clone_git_url()` 後に呼ぶ。 |
| `change_assignee(assignee_id)` | `assignee_id: int` | `None` | 現在タスクの担当者を変更。 |
| `get_assignee()` | なし | `int` | `reporter` を優先して返す（なければ `assignee`）。完了時の担当者復元に利用。 |
| `complete_text(prompt, max_tokens=2048, include_codebase=False)` | `prompt: str`, ... | `str` | Claude に自由記述テキストを生成させて返す。 |
| `run_agent(prompt)` | `prompt: str` | `list[str]` | コードベースを読み `prompt` の改修を Claude に実装させ FILE ブロックを適用。変更ファイルのパス一覧を返す。`clone_git_url()` 後に呼ぶ。 |
| `gh_create_pr(task)` | `task` | `dict` / `None` | 現在ブランチで GitHub PR を作成し、タスク説明に PR リンクを追記。`branch()` 後に呼ぶ。 |

### 3.2 Task CRUD

| メソッド | 引数 | 戻り値 | 説明 |
|----------|------|--------|------|
| `get_task(task_id=None)` | `task_id: int`（省略時は現在のタスク） | `TaskInfo` | タスクをコメント付きで取得。 |
| `create_task(title, ...)` | `title`, `project=None`, `status=1`, `assignee=None`, `task_type=None`, `parent=None`, `event=None`, `description=None`, `progress_summary=None`, `reporter=None`, `deadline=None`, `field_values=None` | `int` | タスクを API 作成し ID を返す。`project`/`assignee`/`event` 未指定時は現タスクから継承。`task_type` は id(int) でも種別名(str) でも可。 |
| `update_task(task_id, **fields)` | `task_id`, `**fields` | `dict` | タスクを PATCH 更新し、更新後の dict を返す。 |
| `delete_task(task_id)` | `task_id` | `None` | タスクを削除。 |
| `create_subtasks(strategy)` | `strategy: Strategy` | `list[int]` | `strategy.subtask_titles` のサブタスクを現タスクの子として作成し ID を返す。 |

### 3.3 Status CRUD（`task_app/statuses/`）

| メソッド | 引数 | 戻り値 | 説明 |
|----------|------|--------|------|
| `get_statuses(project=None)` | `project`（省略時は現タスクのプロジェクト） | `list[dict]` | ステータス一覧を取得。 |
| `get_status(status_id)` | `status_id` | `dict` | ステータスを取得。 |
| `create_status(name, is_done=False, project=None)` | `name`, `is_done`, `project` | `int` | ステータスを作成し ID を返す。`project` 未指定時は現タスクから継承。 |
| `update_status(status_id, **fields)` | `status_id`, `**fields` | `dict` | ステータスを PATCH 更新。 |
| `delete_status(status_id)` | `status_id` | `None` | ステータスを削除。 |

### 3.4 Comment CRUD（`task_app/comments/`）

| メソッド | 引数 | 戻り値 | 説明 |
|----------|------|--------|------|
| `get_comments(task_id=None)` | `task_id`（省略時は現在のタスク） | `list[dict]` | コメント一覧を取得。 |
| `get_comment(comment_id)` | `comment_id` | `dict` | コメントを取得。 |
| `create_comment(message, task=None, author=None)` | `message`, `task`, `author` | `int` | コメントを作成し ID を返す。`task` 未指定時は現タスク、`author` 未指定時は現タスクの担当者を継承。 |
| `update_comment(comment_id, **fields)` | `comment_id`, `**fields` | `dict` | コメントを PATCH 更新。 |
| `delete_comment(comment_id)` | `comment_id` | `None` | コメントを削除。 |
| `post_comment(task, message)` | `task`, `message` | `None` | タスクにコメントを投稿（失敗しても例外を出さない）。 |

### 3.5 Event CRUD（`event_app/events/`）

| メソッド | 引数 | 戻り値 | 説明 |
|----------|------|--------|------|
| `get_events(project=None)` | `project`（任意） | `list[dict]` | イベント一覧を取得。 |
| `get_event(event_id)` | `event_id` | `dict` | イベントを取得。 |
| `create_event(event_date, name=None, project=None, participant_count=None, status=None, previous_event=None)` | 各フィールド | `int` | イベントを作成し ID を返す。`project` 未指定時は現タスクから継承。 |
| `update_event(event_id, **fields)` | `event_id`, `**fields` | `dict` | イベントを PATCH 更新。 |
| `delete_event(event_id)` | `event_id` | `None` | イベントを削除。 |

### 3.6 DSL 実行（`task_app/dsl/execute/`）

| メソッド | 引数 | 戻り値 | 説明 |
|----------|------|--------|------|
| `execute_dsl(dsl)` | `dsl: str` | `int` | DSL スクリプトを API 経由で実行し、実行したコマンド数を返す。 |

### 3.7 実装・コミット・push（細分化パイプライン）

| メソッド | 引数 | 戻り値 | 説明 |
|----------|------|--------|------|
| `implement(task, prompt=None)` | `task`, `prompt` | `list[str]` | Claude にタスクを実装させ FILE ブロックを適用。変更ファイル一覧を返す。`prompt` 未指定時は保存済み Strategy の approach を使用。変更なしなら `RuntimeError`。`clone_git_url()` 後に呼ぶ。 |
| `commit(task)` | `task` | `str` (commit SHA) | 変更をステージしてコミットし commit SHA を返す。 |
| `git_push_only()` | なし | `None` | 現在ブランチを origin に push。`branch()` 後に呼ぶ。 |
| `push(task, prompt=None)` | `task`, `prompt` | `str` (commit SHA) | `implement`→`commit`→`git_push_only` を順に呼び、ステータスをレビュー(4)へ更新、完了コメントを投稿。後方互換のためのラッパー。`clone_git_url()` と `branch()` の後に呼ぶ。 |
| `git_push(task)` | `task` | `str` | `push()` のエイリアス。 |

### 呼び出し順序の前提

1. `ctx.clone_git_url()` — git 操作の前提。
2. `ctx.get_task()` / `ctx.get_kinds()` — タスク情報の取得。
3. `ctx.decide_strategy(task, kinds)` — 実装方針の決定（必要なら `create_subtasks`）。
4. `ctx.branch(task)` — ブランチ作成。
5. `ctx.implement(task)` → `ctx.commit(task)` → `ctx.git_push_only()`
   （または一括で `ctx.push(task)`）。
6. `ctx.gh_create_pr(task)` — PR 作成。
7. `ctx.change_assignee(ctx.get_assignee())` — 起票者へ担当者を戻す。
