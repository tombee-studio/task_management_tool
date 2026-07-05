# Agent Script API リファレンス

このドキュメントは、`Project.agent` フィールドに保存される **Agent Script**（Python）から
利用できる API を調査・整理したものです。Agent Script は `claude-agent/agent.py` の
`execute_agent_script()` によって `ast.parse` 検証後に実行され、`claude-agent/agent_ctx.py`
の `AgentCtx` インスタンスを通じてすべての操作を行います。

- 対象コード: `claude-agent/agent.py` / `claude-agent/agent_ctx.py`
- 実行トリガー: タスクの `assignee` が Automation ユーザーに変更されたとき（CLAUDE.md 参照）
- `Project.agent` が空の場合は `DEFAULT_AGENT_SCRIPT` が実行されます。

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

### 3.1 計画・情報取得

| メソッド | 引数 | 戻り値 | 説明 |
|----------|------|--------|------|
| `get_kinds()` | なし | `list[TaskKind]` | プロジェクトのタスク種別一覧を取得。 |
| `clone_git_url()` | なし | `None` | プロジェクトの `git_url` を一時ディレクトリに clone。git 操作前に必須。`git_url` 未設定時は `RuntimeError`。 |
| `get_task(task_id=None)` | `task_id: int` (省略時は現在のタスク) | `TaskInfo` | タスクをコメント付きで取得。`task_id` を渡すと任意のタスクを取得できる。 |
| `decide_strategy(task, kinds)` | `task: TaskInfo`, `kinds: list[TaskKind]` | `Strategy` | Claude に実装方針を計画させ、内部に保存して返す。 |
| `get_modification_level()` | なし | `int` (`SMALL`/`MIDDLE`/`LARGE`) | Claude に改修規模を判定させる。不明時は `MIDDLE`。 |

### 3.2 Task の CRUD

| メソッド | 引数 | 戻り値 | 説明 |
|----------|------|--------|------|
| `create_task(title, ...)` | `title: str`, `project=None`, `status=1`, `assignee=None`, `task_type=None`, `parent=None`, `event=None`, `description=None`, `progress_summary=None`, `reporter=None`, `deadline=None`, `field_values=None` | `int` | タスクを API 作成し ID を返す。各フィールドをキーワード引数で指定。`project`/`assignee`/`event` 未指定時は現タスクから継承。`task_type` は id(int) でも種別名(str) でも可。 |
| `create_subtasks(strategy)` | `strategy: Strategy` | `list[int]` | `strategy.subtask_titles` のサブタスクを（現タスクの子として）API 作成し、ID を返す。内部で `create_task` に委譲。 |
| `update_task(task_id, **fields)` | `task_id: int`, 任意のフィールド | `dict` | タスクの任意フィールドを PATCH 更新し、更新後の dict を返す。 |
| `delete_task(task_id)` | `task_id: int` | `None` | タスクを削除する。 |

### 3.3 Status の CRUD

| メソッド | 引数 | 戻り値 | 説明 |
|----------|------|--------|------|
| `create_status(name, is_done=False, project=None)` | `name: str`, `is_done: bool`, `project=None` | `int` | ステータスを作成し ID を返す。`project` 未指定時は現タスクのプロジェクトを継承。 |
| `get_status(status_id)` | `status_id: int` | `dict` | ステータスを取得する。 |
| `update_status(status_id, **fields)` | `status_id: int`, 任意のフィールド | `dict` | ステータスを PATCH 更新し、更新後の dict を返す。 |
| `delete_status(status_id)` | `status_id: int` | `None` | ステータスを削除する。 |

### 3.4 Comment の CRUD

| メソッド | 引数 | 戻り値 | 説明 |
|----------|------|--------|------|
| `post_comment(task, message)` | `task`, `message: str` | `None` | タスクにコメントを投稿（失敗しても例外を出さない）。 |
| `create_comment(message, task=None, author=None)` | `message: str`, `task=None`, `author=None` | `int` | コメントを作成し ID を返す。`task` 未指定時は現タスク、`author` 未指定時は現タスクの担当者を継承。 |
| `get_comment(comment_id)` | `comment_id: int` | `dict` | コメントを取得する。 |
| `update_comment(comment_id, **fields)` | `comment_id: int`, 任意のフィールド | `dict` | コメントを PATCH 更新し、更新後の dict を返す。 |
| `delete_comment(comment_id)` | `comment_id: int` | `None` | コメントを削除する。 |

### 3.5 Event の CRUD

| メソッド | 引数 | 戻り値 | 説明 |
|----------|------|--------|------|
| `create_event(event_date, project=None, name=None, participant_count=None, status=None, previous_event=None)` | `event_date: str`, ほか任意 | `int` | イベントを作成し ID を返す。`project` 未指定時は現タスクのプロジェクトを継承。 |
| `get_event(event_id)` | `event_id: int` | `dict` | イベントを取得する。 |
| `update_event(event_id, **fields)` | `event_id: int`, 任意のフィールド | `dict` | イベントを PATCH 更新し、更新後の dict を返す。 |
| `delete_event(event_id)` | `event_id: int` | `None` | イベントを削除する。 |

### 3.6 DSL 実行

| メソッド | 引数 | 戻り値 | 説明 |
|----------|------|--------|------|
| `execute_dsl(dsl)` | `dsl: str` | `int` | DSL スクリプトを `DSLExecuteView`（`dsl/execute/`）へ送信して実行し、実行コマンド数を返す。 |

### 3.7 担当者・git・PR

| メソッド | 引数 | 戻り値 | 説明 |
|----------|------|--------|------|
| `branch(task)` | `task` | `None` | タスクに応じた git ブランチを作成/切替。`clone_git_url()` 後に呼ぶ。 |
| `change_assignee(assignee_id)` | `assignee_id: int` | `None` | 現在タスクの担当者を変更。 |
| `get_assignee()` | なし | `int` | `reporter` を優先して返す（なければ `assignee`）。完了時の担当者復元に利用。 |
| `run_agent(prompt)` | `prompt: str` | `list[str]` | コードベースを読み、`prompt` の改修を Claude に実装させ FILE ブロックを適用。変更ファイルのパス一覧を返す。`clone_git_url()` 後に呼ぶ。 |
| `implement(task)` | `task` | `list[str]` | タスクを実装（`run_agent`）してテストを実行し、変更ファイルのパス一覧を返す。`push()` の第 1 段階。 |
| `commit(task)` | `task` | `str` (commit SHA) | 変更を `git add` + `git commit` し、commit SHA を返す。`push()` の第 2 段階。 |
| `git_push_only()` | なし | `None` | 現在ブランチを `git push` するのみ。`push()` の第 3 段階。 |
| `push(task)` | `task` | `str` (commit SHA) | `implement()` → `commit()` → `git_push_only()` を連結して実行し、ステータスをレビュー(4)へ更新、完了コメントを投稿。`clone_git_url()` と `branch()` の後に呼ぶ。 |
| `git_push(task)` | `task` | `str` | `push()` のエイリアス。 |
| `gh_create_pr(task)` | `task` | `dict` / `None` | 現在ブランチで GitHub PR を作成し、タスク説明に PR リンクを追記。`branch()` 後に呼ぶ。 |

### 呼び出し順序の前提

1. `clone_git_url()` … 以降の git 操作（`branch` / `implement` / `commit` /
   `git_push_only` / `push` / `run_agent` / `gh_create_pr`）の前提。
2. `get_task()` / `get_kinds()` … 対象タスクと種別の取得。
3. `decide_strategy()` … 実装方針の決定（必要なら `create_subtasks()`）。
4. `branch()` … タスク種別に応じたブランチを作成/切替。
5. `push()`（または `implement()` → `commit()` → `git_push_only()`）… 実装・テスト・
   コミット・push。
6. `gh_create_pr()` … PR 作成。
7. `change_assignee(get_assignee())` … 起票者へ担当者を戻す。

`push()` は後方互換のため `implement()` → `commit()` → `git_push_only()` を内部で
連結しつつ、ステータス更新と完了コメント投稿まで行います。細粒度に制御したい場合は
個別メソッドを直接呼び出せます。
