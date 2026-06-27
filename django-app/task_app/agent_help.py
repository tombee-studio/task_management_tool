"""Agent Script API のヘルプ用構造化データ。

プロジェクト編集ページで Agent Script（``Project.agent``）に記述できる
API の一覧とサンプルコードを提供する。

``claude-agent/agent.py`` はスクリプトを ``ast.parse`` で検証したうえで
``exec`` する。実行時にスコープへ注入されるオブジェクト・定数・関数と、
``ctx``（``AgentCtx``）が公開する各メソッドをここで文書化し、UI 側では
このデータをレンダリングするだけにする（ヘルプ内容のメンテナンスを
1 箇所に集約する）。
"""

# ---------------------------------------------------------------------------
# 実行時にスクリプトのスコープへ注入されるグローバル
# (agent.py の execute_agent_script の namespace に対応)
# ---------------------------------------------------------------------------

AGENT_SCRIPT_GLOBALS = [
    {
        'name': 'ctx',
        'type': 'AgentCtx',
        'description': 'エージェントの全操作を提供するコンテキストオブジェクト。'
                       '各メソッドの詳細は下記「ctx のメソッド」を参照。',
    },
    {
        'name': 'task_id',
        'type': 'int',
        'description': '実行中のタスク ID。環境変数 TASK_ID から取得される。',
    },
    {
        'name': 'SMALL / MIDDLE / LARGE',
        'type': 'int',
        'description': '改修規模を表す定数（それぞれ 1 / 2 / 3）。'
                       'ctx.get_modification_level() の戻り値と比較して分岐に使う。',
    },
    {
        'name': 'run_agent(prompt)',
        'type': 'function',
        'description': 'ctx.run_agent(prompt) のショートカット。'
                       'ctx を介さずトップレベルで呼び出せる。',
    },
    {
        'name': 'create_pr(task)',
        'type': 'function',
        'description': 'ctx.gh_create_pr(task) のショートカット。',
    },
]


# ---------------------------------------------------------------------------
# ctx (AgentCtx) が公開するメソッド
# (agent_ctx.py の Public API に対応)
# ---------------------------------------------------------------------------

AGENT_CTX_METHODS = [
    {
        'name': 'clone_git_url',
        'signature': 'ctx.clone_git_url()',
        'params': [],
        'returns': 'None',
        'description': 'プロジェクトの git_url を一時ディレクトリへクローンする。'
                       'branch() / push() / gh_create_pr() / run_agent() を呼ぶ前に'
                       '必ず最初に実行する。git_url 未設定の場合は例外を送出する。',
    },
    {
        'name': 'get_task',
        'signature': 'task = ctx.get_task()',
        'params': [],
        'returns': 'TaskInfo',
        'description': '実行中タスクをコメント付きで取得する。戻り値の TaskInfo は '
                       'id / title / description / status / assignee / reporter / '
                       'parent / project / event / comments / kind 属性を持つ。',
    },
    {
        'name': 'get_kinds',
        'signature': 'kinds = ctx.get_kinds()',
        'params': [],
        'returns': 'list[TaskKind]',
        'description': '対象プロジェクトのタスク種別一覧を TaskKind のリストで返す。'
                       '各 TaskKind は name 属性を持つ。',
    },
    {
        'name': 'decide_strategy',
        'signature': 'strategy = ctx.decide_strategy(task, kinds)',
        'params': [
            {'name': 'task', 'type': 'TaskInfo', 'description': 'get_task() の戻り値。'},
            {'name': 'kinds', 'type': 'list[TaskKind]', 'description': 'get_kinds() の戻り値。'},
        ],
        'returns': 'Strategy',
        'description': 'Claude に実装方針を立案させる。戻り値の Strategy は '
                       'approach（実装方針の文字列）と subtask_titles（サブタスク名のリスト）'
                       'を持つ。決定した方針は内部に保持され push() で利用される。',
    },
    {
        'name': 'get_modification_level',
        'signature': 'level = ctx.get_modification_level()',
        'params': [],
        'returns': 'int (SMALL / MIDDLE / LARGE)',
        'description': 'Claude に改修規模を判定させ、SMALL(1) / MIDDLE(2) / LARGE(3) の'
                       'いずれかを返す。判定不能時は MIDDLE にフォールバックする。',
    },
    {
        'name': 'create_subtasks',
        'signature': 'ids = ctx.create_subtasks(strategy)',
        'params': [
            {'name': 'strategy', 'type': 'Strategy', 'description': 'decide_strategy() の戻り値。'},
        ],
        'returns': 'list[int]',
        'description': 'strategy.subtask_titles に列挙されたサブタスクを API 経由で作成し、'
                       '作成したタスク ID のリストを返す。',
    },
    {
        'name': 'branch',
        'signature': 'ctx.branch(task)',
        'params': [
            {'name': 'task', 'type': 'TaskInfo | dict', 'description': '対象タスク。'},
        ],
        'returns': 'None',
        'description': 'タスク種別に応じた git ブランチを作成または切り替える。'
                       'clone_git_url() の後に呼び出す。',
    },
    {
        'name': 'run_agent',
        'signature': 'changed = ctx.run_agent(prompt)',
        'params': [
            {'name': 'prompt', 'type': 'str', 'description': '実装を依頼する指示文。'},
        ],
        'returns': 'list[str]',
        'description': 'コードベースを読み込み、prompt の内容を Claude に実装させて'
                       'FILE ブロックを適用し、変更されたファイルパスのリストを返す。'
                       'clone_git_url() の後に呼び出す。',
    },
    {
        'name': 'push',
        'signature': 'sha = ctx.push(task)',
        'params': [
            {'name': 'task', 'type': 'TaskInfo | dict', 'description': '対象タスク。'},
        ],
        'returns': 'str (commit SHA)',
        'description': 'Claude にタスクを実装させ、テスト実行・コミット・push まで行う。'
                       'タスク状態を レビュー(4) に更新し、完了コメントを投稿する。'
                       'clone_git_url() と branch() の後に呼び出す。'
                       'git_push(task) は本メソッドの別名。',
    },
    {
        'name': 'gh_create_pr',
        'signature': 'pr = ctx.gh_create_pr(task)',
        'params': [
            {'name': 'task', 'type': 'TaskInfo | dict', 'description': '対象タスク。'},
        ],
        'returns': 'dict | None',
        'description': '現在のブランチに対して GitHub の Pull Request を作成し、'
                       'タスクの説明欄に PR へのリンクを追記する。'
                       'create_pr(task) はショートカット。',
    },
    {
        'name': 'post_comment',
        'signature': 'ctx.post_comment(task, message)',
        'params': [
            {'name': 'task', 'type': 'TaskInfo | dict', 'description': '対象タスク。'},
            {'name': 'message', 'type': 'str', 'description': '投稿するコメント本文。'},
        ],
        'returns': 'None',
        'description': 'タスクにコメントを投稿する。',
    },
    {
        'name': 'change_assignee',
        'signature': 'ctx.change_assignee(assignee_id)',
        'params': [
            {'name': 'assignee_id', 'type': 'int', 'description': '新しい担当者のユーザー ID。'},
        ],
        'returns': 'None',
        'description': '実行中タスクの担当者を変更する。'
                       '通常は完了時に reporter へ戻すために使う。',
    },
    {
        'name': 'get_assignee',
        'signature': 'assignee_id = ctx.get_assignee()',
        'params': [],
        'returns': 'int',
        'description': '完了時に担当者として復元すべきユーザー ID（reporter、'
                       '未設定なら現在の assignee）を返す。',
    },
]


# ---------------------------------------------------------------------------
# サンプルスクリプト
# ---------------------------------------------------------------------------

AGENT_SCRIPT_SAMPLES = [
    {
        'title': 'デフォルトパイプライン',
        'description': 'Agent 設定が空のときに実行される標準フロー。'
                       '初期化 → 方針決定 → 実装・push → PR 作成 → 担当者復元。',
        'code': (
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
        'title': '改修規模に応じてサブタスクを分割する',
        'description': 'get_modification_level() の判定が LARGE のときだけ'
                       'サブタスクを作成してから実装に進む例。',
        'code': (
            "ctx.clone_git_url()\n"
            "task = ctx.get_task()\n"
            "kinds = ctx.get_kinds()\n"
            "strategy = ctx.decide_strategy(task, kinds)\n"
            "\n"
            "if ctx.get_modification_level() >= LARGE:\n"
            "    ctx.create_subtasks(strategy)\n"
            "\n"
            "ctx.branch(task)\n"
            "ctx.push(task)\n"
            "ctx.gh_create_pr(task)\n"
            "ctx.change_assignee(ctx.get_assignee())\n"
        ),
    },
    {
        'title': 'run_agent で個別の指示を与える',
        'description': 'push() の自動プロンプトではなく、run_agent() に独自の'
                       '指示文を渡して実装させる例。変更がなければコメントを残す。',
        'code': (
            "ctx.clone_git_url()\n"
            "task = ctx.get_task()\n"
            "ctx.branch(task)\n"
            "\n"
            "changed = run_agent(\n"
            "    f\"#{task_id} {task.title} を実装してください。\\n\"\n"
            "    f\"{task.description}\"\n"
            ")\n"
            "\n"
            "if not changed:\n"
            "    ctx.post_comment(task, \"変更すべきファイルを特定できませんでした。\")\n"
            "else:\n"
            "    ctx.push(task)\n"
            "    create_pr(task)\n"
            "    ctx.change_assignee(ctx.get_assignee())\n"
        ),
    },
]


def get_agent_help():
    """Agent Script API ヘルプ全体を 1 つの dict にまとめて返す。"""
    return {
        'globals': AGENT_SCRIPT_GLOBALS,
        'methods': AGENT_CTX_METHODS,
        'samples': AGENT_SCRIPT_SAMPLES,
    }
