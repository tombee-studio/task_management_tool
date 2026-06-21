from datetime import timedelta, date
from .models import Task


def build_gantt_data(project, from_date=None, to_date=None, assignee_ids=None,
                     status_filter='active', task_qs=None, event_qs=None):
    if event_qs is not None:
        events = list(event_qs.order_by('event_date'))
    else:
        events = list(project.event_set.order_by('event_date'))

    if task_qs is None:
        task_qs = Task.objects.filter(project=project)
        if assignee_ids is not None:
            task_qs = task_qs.filter(assignee_id__in=assignee_ids)
        if status_filter == 'active':
            task_qs = task_qs.filter(status__is_done=False)
        elif status_filter == 'done':
            task_qs = task_qs.filter(status__is_done=True)
    else:
        # Apply filters even when task_qs is provided externally
        if assignee_ids is not None:
            task_qs = task_qs.filter(assignee_id__in=assignee_ids)
        if status_filter == 'active':
            task_qs = task_qs.filter(status__is_done=False)
        elif status_filter == 'done':
            task_qs = task_qs.filter(status__is_done=True)

    tasks = list(task_qs)

    today = date.today()

    if from_date is None or to_date is None:
        dates = [today]
        for event in events:
            dates.append(event.event_date)
        for task in tasks:
            if task.created_at:
                dates.append(task.created_at.date())
            if task.deadline:
                dates.append(task.deadline)
        auto_min = min(dates) - timedelta(days=7)
        auto_max = max(dates) + timedelta(days=14)
        if from_date is None:
            from_date = auto_min
        if to_date is None:
            to_date = auto_max

    if from_date > to_date:
        from_date, to_date = to_date, from_date

    min_date, max_date = from_date, to_date
    total_days = (max_date - min_date).days or 1

    def to_pct(d):
        return round((d - min_date).days / total_days * 100, 2)

    date_labels = []
    d = date(min_date.year, min_date.month, 1)
    while d <= max_date:
        pct = to_pct(d)
        if 0 <= pct <= 100:
            date_labels.append({'label': d.strftime('%Y/%m'), 'pct': pct})
        d = date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)

    today_pct = to_pct(today)

    event_items = []
    for event in events:
        if min_date <= event.event_date <= max_date:
            event_items.append({'event': event, 'pct': to_pct(event.event_date)})

    task_items = []
    for task in tasks:
        start = task.created_at.date() if task.created_at else today
        end = task.deadline
        if end:
            if end < start:
                start = end
            if end < min_date or start > max_date:
                continue
            start_pct = to_pct(start)
            width_pct = round(max(to_pct(end) - start_pct, 0.5), 2)
        else:
            if not (min_date <= start <= max_date):
                continue
            start_pct = to_pct(start)
            width_pct = None
        task_items.append({
            'task': task,
            'depth': 0,
            'margin_left': 0,
            'start_pct': start_pct,
            'width_pct': width_pct,
            'has_deadline': bool(task.deadline),
        })

    return {
        'min_date': min_date,
        'max_date': max_date,
        'today_pct': today_pct,
        'date_labels': date_labels,
        'events': event_items,
        'tasks': task_items,
        'day_pct': round(100 / total_days, 4),
    }
