import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db import transaction
from lark import Lark, Transformer

from .models import Task

_GRAMMAR = (Path(__file__).parent / "dsl_grammar.lark").read_text()

_STATEMENT_RE = re.compile(
    r"^\s*(LINK|TAG|PARENT|ASSIGN)\b",
    re.IGNORECASE,
)

_parser = Lark(_GRAMMAR, parser="lalr", start="start")


class _DslTransformer(Transformer):
    """パースツリーをコマンドタプルの AST に変換する。

    LARK はルール名と同名のメソッドを自動的に呼び出す。
    各メソッドの args には子ノードを変換済みの値が渡される。
    """

    def link_stmt(self, args):
        """LINK コマンドを ("link", src_id, dst_id) に変換する。"""
        return ("link", int(args[0]), int(args[1]))

    def tag_stmt(self, args):
        """TAG コマンドを ("tag", task_id, tag_name) に変換する。"""
        return ("tag", int(args[0]), args[1])

    def parent_stmt(self, args):
        """PARENT コマンドを ("parent", child_id, parent_id) に変換する。"""
        return ("parent", int(args[0]), int(args[1]))

    def assign_stmt(self, args):
        """ASSIGN コマンドを ("assign", task_id, username) に変換する。"""
        return ("assign", int(args[0]), args[1])

    def name_or_string(self, args):
        """識別子またはクォート文字列を Python の str に変換する。

        LARK の ESCAPED_STRING トークンはクォートを含む ("alice" のまま) ため、
        ここで両端のダブルクォートを除去する。裸の NAME はそのまま返す。
        """
        s = str(args[0])
        if len(s) >= 2 and s[0] == '"':
            return s[1:-1]
        return s

    def start(self, args):
        """トップレベルの全ステートメントをリストにまとめて返す。"""
        return list(args)


_transformer = _DslTransformer()


def parse_dsl(text):
    """DSL テキストを解析し、コマンドタプルのリスト (AST) を返す。

    各タプルの先頭要素がコマンド種別:
      ("link",   src_id, dst_id)
      ("tag",    task_id, tag_name)      # future
      ("parent", child_id, parent_id)   # future
      ("assign", task_id, username)     # future

    既知キーワードで始まらない行はすべて無視する。
    これにより、ルールテンプレートに自由記述が混在しても後方互換性を保てる。
    """
    lines = [
        line.strip()
        for line in text.splitlines()
        if _STATEMENT_RE.match(line)
    ]
    if not lines:
        return []
    tree = _parser.parse("\n".join(lines))
    return _transformer.transform(tree)


def execute_link(src_id, dst_id):
    """src と dst を related_tasks で双方向に紐付ける。

    どちらかの ID が存在しない場合は何もしない。
    ルールテンプレートが古い ID を参照していても例外を出さないようにするため。
    """
    try:
        src = Task.objects.get(pk=src_id)
        dst = Task.objects.get(pk=dst_id)
    except Task.DoesNotExist:
        return
    src.related_tasks.add(dst)


def execute_assign(task_id, username):
    """タスクの担当者をユーザー名で変更する。

    タスクまたはユーザーが存在しない場合は何もしない。
    """
    User = get_user_model()
    try:
        task = Task.objects.get(pk=task_id)
        user = User.objects.get(username=username)
    except (Task.DoesNotExist, User.DoesNotExist):
        return
    task.assignee = user
    task.save()


def execute_ast(ast):
    """AST の各コマンドを対応する execute_* 関数にディスパッチする。

    未実装のコマンド (tag / parent) はパース済みだが実行をスキップする。
    """
    for command in ast:
        command_type = command[0]
        if command_type == "link":
            _, src_id, dst_id = command
            execute_link(src_id, dst_id)
        elif command_type == "assign":
            _, task_id, username = command
            execute_assign(task_id, username)


@transaction.atomic
def execute_dsl(text):
    """DSL テキストを解析して実行する。

    いずれかのコマンドが失敗した場合、トランザクション全体をロールバックする。
    """
    ast = parse_dsl(text)
    execute_ast(ast)
