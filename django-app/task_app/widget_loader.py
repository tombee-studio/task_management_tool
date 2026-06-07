import yaml
from django.db.models import Q
from .filters import parse_search_query, apply_task_filters
from .models import Task
from .gantt import build_gantt_data

DEFAULT_WIDGET_CONFIG = """\
pages:
  - name: project_list
    widgets:
      - title: 自分のタスク一覧
        rules:
          - table: task
            filter: "assignee=me status__is_done=False"
        type: table
        order:
          - task
      - title: ウォッチしているタスク一覧
        rules:
          - table: task
            source: watched_tasks
            filter: "status__is_done=False"
        type: tree
        order:
          - task
  - name: project_detail
    widgets:
      - title: 未完了のイベント一覧
        rules:
          - table: event
            filter: "status__is_done=False"
        type: tree
        order:
          - event
      - title: 未完了のタスク一覧
        rules:
          - table: task
            filter: "status__is_done=False"
        type: table
        order:
          - task
  - name: task_detail
    widgets:
      - title: 関連するイベント
        rules:
          - table: event
            source: task_event
        type: table
        order:
          - event
      - title: 関連タスク
        rules:
          - table: task
            source: related_tasks
        type: table
        order:
          - task
      - title: サブタスク（未完了）
        rules:
          - table: task
            source: subtasks
            filter: "status__is_done=False"
        type: table
        order:
          - task
"""


def parse_widget_config(config_str):
    """YAML 文字列をパースして dict を返す。エラー時は {} を返す。"""
    if not config_str or not config_str.strip():
        return {}
    try:
        result = yaml.safe_load(config_str)
        return result if isinstance(result, dict) else {}
    except yaml.YAMLError:
        return {}


def get_page_widgets(config_str, page_name):
    """指定ページ名に対応するウィジェット設定リストを返す。"""
    config = parse_widget_config(config_str)
    pages = config.get('pages', [])
    if not isinstance(pages, list):
        return []
    for page in pages:
        if isinstance(page, dict) and page.get('name') == page_name:
            return page.get('widgets') or []
    return []


def _base_task_qs(user, project=None):
    qs = Task.objects.filter(
        Q(project__participants=user) | Q(assignee=user)
    ).distinct().select_related('project', 'status', 'assignee')
    if project is not None:
        qs = qs.filter(project=project)
    return qs


def _base_event_qs(user, project=None):
    from event_app.models import Event
    qs = Event.objects.filter(
        project__participants=user
    ).distinct().select_related('project', 'status')
    if project is not None:
        qs = qs.filter(project=project)
    return qs


def _apply_event_filter(qs, filter_str):
    """イベントへの基本フィルタ。"""
    if not filter_str or not filter_str.strip():
        return qs
    for token in filter_str.split():
        if '=' in token:
            key, _, value = token.partition('=')
            if key == 'status__is_done':
                is_done = value.lower() not in ('false', '0', 'no')
                qs = qs.filter(status__is_done=is_done)
    return qs


def _resolve_source_task_qs(source, user, project, task, filter_str):
    """source フィールドに基づいてタスク QuerySet を返す。"""
    if source == 'watched_tasks':
        qs = user.watches.all().select_related('project', 'status', 'assignee')
        if project is not None:
            qs = qs.filter(project=project)
        parsed = parse_search_query(filter_str, user=user)
        return apply_task_filters(qs, parsed)

    if task is None:
        return Task.objects.none()

    if source == 'subtasks':
        qs = task.tasks.all().select_related('project', 'status', 'assignee')
        parsed = parse_search_query(filter_str, user=user)
        return apply_task_filters(qs, parsed)

    if source == 'related_tasks':
        qs = task.related_tasks.all().select_related('project', 'status', 'assignee')
        parsed = parse_search_query(filter_str, user=user)
        return apply_task_filters(qs, parsed)

    return Task.objects.none()


def _resolve_source_event_qs(source, task):
    """source フィールドに基づいてイベント QuerySet を返す。"""
    if source == 'task_event' and task is not None:
        from event_app.models import Event
        if task.event_id is not None:
            return Event.objects.filter(pk=task.event_id).select_related('project', 'status')
        return Event.objects.none()
    return None


def build_task_tree(task_qs):
    """タスク QuerySet を親子関係に基づいて木構造に変換する。
    各タスクに _tree_children 属性を付与し、ルートタスクのリストを返す。
    """
    tasks = list(task_qs)
    task_map = {t.pk: t for t in tasks}
    task_ids = set(task_map.keys())

    for t in tasks:
        t._tree_children = []

    roots = []
    for t in tasks:
        if t.parent_id is not None and t.parent_id in task_ids:
            task_map[t.parent_id]._tree_children.append(t)
        else:
            roots.append(t)

    return roots


def flatten_task_tree(roots):
    """build_task_tree の結果を {'task': task, 'depth': int} のフラットリストに変換する。"""
    result = []

    def _traverse(tasks, depth):
        for t in tasks:
            result.append({'task': t, 'depth': depth})
            _traverse(t._tree_children, depth + 1)

    _traverse(roots, 0)
    return result


def resolve_widget_data(widget_config, user, project=None, task=None):
    """
    ウィジェット設定 dict からデータを解決して返す。

    返り値の keys:
        title, type, tasks, events, gantt, gantt_per_project, order, columns, error
    """
    if not isinstance(widget_config, dict):
        return {'error': '無効なウィジェット設定です', 'title': '', 'type': 'table'}

    title = widget_config.get('title', '')
    widget_type = widget_config.get('type', 'table')
    rules = widget_config.get('rules') or []
    order = widget_config.get('order') or ['task', 'event']
    columns = widget_config.get('columns') or []

    task_qs = None
    event_qs = None

    for rule in rules:
        if not isinstance(rule, dict):
            continue
        table = rule.get('table', '')
        source = rule.get('source') or ''
        filter_str = rule.get('filter') or ''

        if table == 'task':
            if source:
                task_qs = _resolve_source_task_qs(source, user, project, task, filter_str)
            else:
                base = _base_task_qs(user, project=project)
                parsed = parse_search_query(filter_str, user=user)
                task_qs = apply_task_filters(base, parsed)
        elif table == 'event':
            if source:
                resolved = _resolve_source_event_qs(source, task)
                if resolved is not None:
                    event_qs = resolved
            else:
                base = _base_event_qs(user, project=project)
                event_qs = _apply_event_filter(base, filter_str)

    task_tree = None
    gantt = None
    gantt_per_project = None

    if widget_type == 'tree' and task_qs is not None:
        roots = build_task_tree(task_qs)
        task_tree = flatten_task_tree(roots)

    if widget_type == 'gantt':
        if project is not None:
            gantt = build_gantt_data(project, task_qs=task_qs, event_qs=event_qs)
        else:
            user_projects = user.projects.all()
            gantt_per_project = []
            for proj in user_projects:
                proj_task_qs = task_qs.filter(project=proj) if task_qs is not None else None
                proj_event_qs = event_qs.filter(project=proj) if event_qs is not None else None
                gantt_per_project.append({
                    'project': proj,
                    'gantt': build_gantt_data(proj, task_qs=proj_task_qs, event_qs=proj_event_qs),
                })

    return {
        'title': title,
        'type': widget_type,
        'tasks': task_qs,
        'task_tree': task_tree,
        'events': event_qs,
        'gantt': gantt,
        'gantt_per_project': gantt_per_project,
        'order': order,
        'columns': columns,
        'error': None,
    }
