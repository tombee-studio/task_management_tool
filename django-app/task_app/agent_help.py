"""Agent Script ヘルプコンテンツ.

種別編集ページの Agent Script（`TaskType.agent`）入力欄付近に表示する、
API リファレンスとサンプルスクリプト（実行フロー含む）を構造化データとして管理する。

メンテナンス性のため、利用可能な API 一覧・各 API の説明・サンプルコード・処理の流れを
このモジュールで一元管理する。詳細な調査結果は `claude-agent/AGENT_API.md` を参照。

対象コード:
  - claude-agent/agent.py        … execute_agent_script() / namespace 注入
  - claude-agent/agent_ctx.py    … AgentCtx / TaskInfo / Strategy / TaskKind
"""

# スクリプトのスコープに注入されるトップレベル名
AGENT_SCRIPT_GLOBALS = [
    {"name": "ctx", "kind": "AgentCtx",
     "description": "エージェント操作の本体。すべての処理はこのオブジェクト経由で呼び出す。"},
    {"name": "task_id", "kind": "int",
     "description": "現在処理しているタスクの ID（環境変数 TASK_ID）。"},
    {"name": "SMALL", "kind": "int (=1)",
     "description": "改修規模の定数（小）。"},
    {"name": "MIDDLE", "kind": "int (=2)",
     "description": "改修規模の定数（中）。"},
    {"name": "LARGE", "kind": "int (=3)",
     "description": "改修規模の定数（大）。"},
    {"name": "run_agent", "kind": "callable",
     "description": "ctx.run_agent へのトップレベル別名。"},
    {"name": "create_pr", "kind": "callable",
     "description": "ctx.gh_create_pr へのトップレベル別名。"},
    {"name": "execute_dsl", "kind": "callable",
     "description": "ctx.execute_dsl へのトップレベル別名。"},
]

# 利用可能な組み込み関数（_SAFE_BUILTINS）
AGENT_SAFE_BUILTINS = [
    "print", "range", "len", "str", "int", "float", "bool", "list", "dict",
    "tuple", "enumerate", "zip", "True", "False", "None",
]

# AgentCtx の公開 API リファレンス（クラス・メソッド・引数・戻り値）
AGENT_API_REFERENCE = [
    {
        "method": "ctx.get_kinds()",
        "params": "なし",
        "returns": "list[TaskKind]",
        "description": "プロジェクトのタスク種別一覧を取得する。",
    },
    {
        "method": "ctx.clone_git_url()",
        "params": "なし",
        "returns": "None",
        "description": (
            "プロジェクトの git_url を一時ディレクトリに clone する。"
            "git 操作前に必須。git_url 未設定時は RuntimeError。"
        ),
    },
    {
        "method": "ctx.get_task(task_id=None)",
        "params": "task_id: int（省略時は現在のタスク）",
        "returns": "TaskInfo",
        "description": "タスクをコメント付きで取得する。task_id を渡すと任意のタスクを取得できる。",
    },
    {
        "method": "ctx.decide_strategy(task, kinds)",
        "params": "task: TaskInfo, kinds: list[TaskKind]",
        "returns": "Strategy",
        "description": "Claude に実装方針を計画させ、内部に保存して返す。",
    },
    {
        "method": "ctx.get_modification_level()",
        "params": "なし",
        "returns": "int (SMALL/MIDDLE/LARGE)",
        "description": "Claude に改修規模を判定させる。不明時は MIDDLE。",
    },
    {
        "method": "ctx.create_task(title, ...)",
        "params": (
            "title: str, project=None, status=1, assignee=None, task_type=None, "
            "parent=None, event=None, description=None, progress_summary=None, "
            "reporter=None, deadline=None, field_values=None"
        ),
        "returns": "int",
        "description": (
            "タスクを API 作成し ID を返す。各フィールドをキーワード引数で指定。"
            "project/assignee/event 未指定時は現タスクから継承、status は 1(未着手)。"
            "task_type は id(int) でも種別名(str) でも可。"
        ),
    },
    {
        "method": "ctx.update_task(task_id, **fields)",
        "params": "task_id: int, **fields",
        "returns": "dict",
        "description": "タスクを PATCH 更新し、更新後の dict を返す。",
    },
    {
        "method": "ctx.delete_task(task_id)",
        "params": "task_id: int",
        "returns": "None",
        "description": "タスクを削除する。",
    },
    {
        "method": "ctx.create_subtasks(strategy)",
        "params": "strategy: Strategy",
        "returns": "list[int]",
        "description": "strategy.subtask_titles のサブタスクを API 作成し、ID を返す。",
    },
    {
        "method": "ctx.get_statuses(project=None)",
        "params": "project: int（省略時は現タスクのプロジェクト）",
        "returns": "list[dict]",
        "description": "ステータス一覧を取得する（task_app/statuses/）。",
    },
    {
        "method": "ctx.get_status(status_id)",
        "params": "status_id: int",
        "returns": "dict",
        "description": "ステータスを 1 件取得する。",
    },
    {
        "method": "ctx.create_status(name, is_done=False, project=None)",
        "params": "name: str, is_done: bool, project=None",
        "returns": "int",
        "description": (
            "ステータスを作成し ID を返す。project 未指定時は現タスクから継承。"
        ),
    },
    {
        "method": "ctx.update_status(status_id, **fields)",
        "params": "status_id: int, **fields",
        "returns": "dict",
        "description": "ステータスを PATCH 更新する。",
    },
    {
        "method": "ctx.delete_status(status_id)",
        "params": "status_id: int",
        "returns": "None",
        "description": "ステータスを削除する。",
    },
    {
        "method": "ctx.get_comments(task_id=None)",
        "params": "task_id: int（省略時は現在のタスク）",
        "returns": "list[dict]",
        "description": "コメント一覧を取得する（task_app/comments/）。",
    },
    {
        "method": "ctx.get_comment(comment_id)",
        "params": "comment_id: int",
        "returns": "dict",
        "description": "コメントを 1 件取得する。",
    },
    {
        "method": "ctx.create_comment(message, task=None, author=None)",
        "params": "message: str, task=None, author=None",
        "returns": "int",
        "description": (
            "コメントを作成し ID を返す。task 未指定時は現タスク、"
            "author 未指定時は現タスクの担当者を継承。"
        ),
    },
    {
        "method": "ctx.update_comment(comment_id, **fields)",
        "params": "comment_id: int, **fields",
        "returns": "dict",
        "description": "コメントを PATCH 更新する。",
    },
    {
        "method": "ctx.delete_comment(comment_id)",
        "params": "comment_id: int",
        "returns": "None",
        "description": "コメントを削除する。",
    },
    {
        "method": "ctx.get_events(project=None)",
        "params": "project: int（任意）",
        "returns": "list[dict]",
        "description": "イベント一覧を取得する（event_app/events/）。",
    },
    {
        "method": "ctx.get_event(event_id)",
        "params": "event_id: int",
        "returns": "dict",
        "description": "イベントを 1 件取得する。",
    },
    {
        "method": "ctx.create_event(event_date, name=None, project=None, ...)",
        "params": (
            "event_date: str, name=None, project=None, participant_count=None, "
            "status=None, previous_event=None"
        ),
        "returns": "int",
        "description": (
            "イベントを作成し ID を返す。project 未指定時は現タスクから継承。"
        ),
    },
    {
        "method": "ctx.update_event(event_id, **fields)",
        "params": "event_id: int, **fields",
        "returns": "dict",
        "description": "イベントを PATCH 更新する。",
    },
    {
        "method": "ctx.delete_event(event_id)",
        "params": "event_id: int",
        "returns": "None",
        "description": "イベントを削除する。",
    },
    {
        "method": "ctx.execute_dsl(dsl)",
        "params": "dsl: str",
        "returns": "int",
        "description": (
            "DSL スクリプトを API 経由で実行し（task_app/dsl/execute/）、"
            "実行したコマンド数を返す。"
        ),
    },
    {
        "method": "ctx.branch(task)",
        "params": "task",
        "returns": "None",
        "description": (
            "タスクに応じた git ブランチを作成/切替する。clone_git_url() 後に呼ぶ。"
        ),
    },
    {
        "method": "ctx.post_comment(task, message)",
        "params": "task, message: str",
        "returns": "None",
        "description": "タスクにコメントを投稿する（失敗しても例外を出さない）。",
    },
    {
        "method": "ctx.change_assignee(assignee_id)",
        "params": "assignee_id: int",
        "returns": "None",
        "description": "現在タスクの担当者を変更する。",
    },
    {
        "method": "ctx.get_assignee()",
        "params": "なし",
        "returns": "int",
        "description": (
            "reporter を優先して返す（なければ assignee）。完了時の担当者復元に利用する。"
        ),
    },
    {
        "method": "ctx.complete_text(prompt, max_tokens=2048, include_codebase=False)",
        "params": "prompt: str, max_tokens: int, include_codebase: bool",
        "returns": "str",
        "description": (
            "Claude に自由記述のテキストを生成させて返す。要約・タイトル・説明など"
            "散文が欲しいときに使う。コード生成用の内部メソッドと違い FILE ブロックを"
            "強制しないため、'FILE: docs/design/*.md' のような出力にならない。"
            "include_codebase=True にすると、クローン済みリポジトリの内容を前置し、"
            "実在するファイルパスのみを使うよう指示する（存在しないパスの創作を防ぐ）。"
            "clone_git_url() 後に呼ぶこと。"
        ),
    },
    {
        "method": "ctx.run_agent(prompt)",
        "params": "prompt: str",
        "returns": "list[str]",
        "description": (
            "コードベースを読み、prompt の改修を Claude に実装させ FILE ブロックを適用する。"
            "変更ファイルのパス一覧を返す。clone_git_url() 後に呼ぶ。"
        ),
    },
    {
        "method": "ctx.implement(task, prompt=None)",
        "params": "task, prompt: str（省略時は Strategy の approach）",
        "returns": "list[str]",
        "description": (
            "Claude にタスクを実装させ FILE ブロックを適用し、変更ファイル一覧を返す。"
            "変更がなければ RuntimeError。clone_git_url() 後に呼ぶ。"
        ),
    },
    {
        "method": "ctx.commit(task)",
        "params": "task",
        "returns": "str (commit SHA)",
        "description": "変更をステージしてコミットし、commit SHA を返す。",
    },
    {
        "method": "ctx.git_push_only()",
        "params": "なし",
        "returns": "None",
        "description": "現在ブランチを origin に push する。branch() 後に呼ぶ。",
    },
    {
        "method": "ctx.push(task, prompt=None)",
        "params": "task, prompt: str（任意）",
        "returns": "str (commit SHA)",
        "description": (
            "implement→commit→git_push_only を順に呼び、ステータスをレビュー(4)へ更新、"
            "完了コメントを投稿する。後方互換のためのラッパー。"
            "clone_git_url() と branch() の後に呼ぶ。"
        ),
    },
    {
        "method": "ctx.git_push(task)",
        "params": "task",
        "returns": "str",
        "description": "push() のエイリアス。",
    },
    {
        "method": "ctx.gh_create_pr(task)",
        "params": "task",
        "returns": "dict / None",
        "description": (
            "現在ブランチで GitHub PR を作成し、タスク説明に PR リンクを追記する。"
            "branch() 後に呼ぶ。"
        ),
    },
]

# 戻り値で使われるデータクラス
AGENT_DATA_CLASSES = [
    {
        "name": "TaskKind",
        "description": "タスクの種別を表す軽量クラス。",
        "members": [
            {"name": "name", "type": "str", "description": "種別名（例: feature, bugfix）。"},
        ],
    },
    {
        "name": "TaskInfo",
        "description": "ctx.get_task() が返すタスク情報。",
        "members": [
            {"name": "id", "type": "int", "description": "タスク ID"},
            {"name": "title", "type": "str", "description": "タイトル"},
            {"name": "description", "type": "str", "description": "説明"},
            {"name": "status", "type": "int / None", "description": "ステータス ID"},
            {"name": "assignee", "type": "int / None", "description": "担当者ユーザー ID"},
            {"name": "reporter", "type": "int / None", "description": "起票者ユーザー ID"},
            {"name": "parent", "type": "int / None", "description": "親タスク ID"},
            {"name": "project", "type": "int", "description": "プロジェクト ID"},
            {"name": "event", "type": "int / None", "description": "紐づくイベント ID"},
            {"name": "comments", "type": "list[dict]", "description": "コメント一覧"},
            {"name": "kind", "type": "TaskKind / None", "description": "タスク種別"},
        ],
    },
    {
        "name": "Strategy",
        "description": "ctx.decide_strategy() が返す実装方針。",
        "members": [
            {"name": "approach", "type": "str", "description": "実装方針の説明"},
            {"name": "subtask_titles", "type": "list[str]",
             "description": "生成すべきサブタスクのタイトル（不要なら空リスト）"},
        ],
    },
]

# サンプルスクリプト（実行フローを示す）
AGENT_SAMPLE_SCRIPTS = [
    {
        "title": "デフォルトパイプライン",
        "description": (
            "タスク種別に Agent スクリプトが設定されていないときに実行される標準フロー。"
            "clone → タスク取得 → 方針決定 → ブランチ → 実装/push → PR → 担当者復元。"
        ),
        "code": (
            "ctx.clone_git_url()\n"
            "task = ctx.get_task()\n"
            "kinds = ctx.get_kinds()\n"
            "ctx.decide_strategy(task, kinds)\n"
            "ctx.branch(task)\n"
            "ctx.push(task)\n"
            "ctx.gh_create_pr(task)\n"
            "ctx.change_assignee(ctx.get_assignee())\n"
        ),
    },
    {
        "title": "implement / commit / push を段階的に呼ぶ",
        "description": (
            "push() の細分化メソッドを使って、実装・コミット・push を個別に制御する。"
        ),
        "code": (
            "ctx.clone_git_url()\n"
            "task = ctx.get_task()\n"
            "ctx.branch(task)\n"
            "changed = ctx.implement(task, 'README に使い方を追記してください。')\n"
            "print(changed)\n"
            "sha = ctx.commit(task)\n"
            "ctx.git_push_only()\n"
            "ctx.gh_create_pr(task)\n"
            "ctx.change_assignee(ctx.get_assignee())\n"
        ),
    },
    {
        "title": "execute_dsl でタスク関係を操作する",
        "description": (
            "DSL を API 経由で実行し、LINK / ASSIGN / EVENT などのコマンドを適用する。"
        ),
        "code": (
            "count = execute_dsl('LINK 1 -> 2\\nASSIGN 1 TO alice')\n"
            "print(count)\n"
        ),
    },
    {
        "title": "改修規模に応じてサブタスクを分割する",
        "description": (
            "get_modification_level() で規模を判定し、LARGE のときだけサブタスクを生成する。"
        ),
        "code": (
            "ctx.clone_git_url()\n"
            "task = ctx.get_task()\n"
            "kinds = ctx.get_kinds()\n"
            "strategy = ctx.decide_strategy(task, kinds)\n"
            "if ctx.get_modification_level() >= LARGE:\n"
            "    ctx.create_subtasks(strategy)\n"
            "ctx.branch(task)\n"
            "ctx.push(task)\n"
            "ctx.gh_create_pr(task)\n"
            "ctx.change_assignee(ctx.get_assignee())\n"
        ),
    },
]

# 処理の流れ（ステップ説明 / シーケンス）
AGENT_EXECUTION_FLOW = [
    {"step": 1, "title": "リポジトリの clone",
     "api": "ctx.clone_git_url()",
     "description": "git_url を一時ディレクトリへ clone する。以降の git 操作の前提。"},
    {"step": 2, "title": "タスク情報の取得",
     "api": "ctx.get_task() / ctx.get_kinds()",
     "description": "対象タスクと種別一覧を取得する。"},
    {"step": 3, "title": "実装方針の決定",
     "api": "ctx.decide_strategy(task, kinds)",
     "description": "Claude に方針を計画させ、必要ならサブタスクを生成する。"},
    {"step": 4, "title": "ブランチ作成",
     "api": "ctx.branch(task)",
     "description": "タスク種別に応じたブランチを作成/切替する。"},
    {"step": 5, "title": "実装・コミット・push",
     "api": "ctx.implement(task) / ctx.commit(task) / ctx.git_push_only()（または ctx.push(task)）",
     "description": "実装→コミット→push し、ステータスをレビュー(4)へ更新する。"},
    {"step": 6, "title": "PR 作成",
     "api": "ctx.gh_create_pr(task)",
     "description": "現在ブランチで PR を作成し、タスク説明にリンクを追記する。"},
    {"step": 7, "title": "担当者の復元",
     "api": "ctx.change_assignee(ctx.get_assignee())",
     "description": "起票者（reporter）へ担当者を戻す。"},
]


def get_agent_help():
    """プロジェクト編集ページで表示する Agent Script ヘルプ全体を返す。"""
    return {
        "globals": AGENT_SCRIPT_GLOBALS,
        "safe_builtins": AGENT_SAFE_BUILTINS,
        "data_classes": AGENT_DATA_CLASSES,
        "api_reference": AGENT_API_REFERENCE,
        "sample_scripts": AGENT_SAMPLE_SCRIPTS,
        "execution_flow": AGENT_EXECUTION_FLOW,
    }
