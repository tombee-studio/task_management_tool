import yaml
from django.db.models import Q
from .filters import parse_search_query, apply_task_filters
from .models import Task
from .gantt import build_gantt_data


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
    """イベントへの基本フィルタ（将来的に拡張可能）。"""
    if not filter_str or not filter_str.strip():
        return qs
    for token in filter_str.split():
        if '=' in token:
            key, _, value = token.partition('=')
            if key == 'status__is_done':
                is_done = value.lower() not in ('false', '0', 'no')
                qs = qs.filter(status__is_done=is_done)
    return qs


def resolve_widget_data(widget_config, user, project=None):
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
        filter_str = rule.get('filter') or ''

        if table == 'task':
            base = _base_task_qs(user, project=project)
            parsed = parse_search_query(filter_str, user=user)
            task_qs = apply_task_filters(base, parsed)
        elif table == 'event':
            base = _base_event_qs(user, project=project)
            event_qs = _apply_event_filter(base, filter_str)

    gantt = None
    gantt_per_project = None

    if widget_type == 'gantt':
        if project is not None:
            gantt = build_gantt_data(project, task_qs=task_qs, event_qs=event_qs)
        else:
            # project_list コンテキスト: プロジェクトごとにガントを生成
            from django.contrib.auth.models import User as AuthUser
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
        'events': event_qs,
        'gantt': gantt,
        'gantt_per_project': gantt_per_project,
        'order': order,
        'columns': columns,
        'error': None,
    }
