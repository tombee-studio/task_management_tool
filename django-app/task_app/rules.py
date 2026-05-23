import re
from .models import Rule
from .dsl import execute_dsl


def process_task_rules(task, text=None):
    """Process rules for a task.

    If `text` is provided, pattern matching uses that text instead of the task's description.
    """
    content = text if text is not None else task.description
    rules = Rule.objects.filter(project=task.project, enabled=True)
    for rule in rules:
        match = re.search(rule.pattern, content)
        if not match:
            continue
        context = {"task_id": task.id}
        for i, value in enumerate(match.groups(), start=1):
            context[f"group{i}"] = value
        dsl = rule.dsl_template.format(**context)
        execute_dsl(dsl)
