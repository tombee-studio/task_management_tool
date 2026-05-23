import re
from django.db import transaction
from .models import Task


LINK_RE = re.compile(r"LINK\s+(\d+)\s*->\s*(\d+)", re.IGNORECASE)


def parse_dsl(text):
    """Return AST as list of tuples like ("link", src_id, dst_id)."""
    ast = []
    for line in text.splitlines():
        m = LINK_RE.search(line)
        if m:
            src = int(m.group(1))
            dst = int(m.group(2))
            ast.append(("link", src, dst))
    return ast


def execute_link(src_id, dst_id):
    try:
        src = Task.objects.get(pk=src_id)
        dst = Task.objects.get(pk=dst_id)
    except Task.DoesNotExist:
        return
    # Use existing related_tasks relationship for task links
    src.related_tasks.add(dst)


def execute_ast(ast):
    for command in ast:
        command_type = command[0]
        if command_type == "link":
            _, src_id, dst_id = command
            execute_link(src_id, dst_id)


@transaction.atomic
def execute_dsl(text):
    ast = parse_dsl(text)
    execute_ast(ast)
