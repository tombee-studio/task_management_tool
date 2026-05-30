import re
from datetime import timedelta, date
from django.utils import timezone
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.db.models import Count, Prefetch, Q
from .models import *

from django.contrib.auth import login
from django.http import HttpResponseRedirect
from .forms import SignUpForm, ProjectForm, TaskForm, CommentForm


def _parse_gantt_date(value):
    """GET パラメータの文字列を date に変換。不正値は None を返す。"""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def build_gantt_data(project, from_date=None, to_date=None):
    events = list(project.event_set.order_by('event_date'))
    tasks = list(Task.objects.with_tree_fields().filter(project=project))

    today = date.today()

    # 指定がない軸は自動計算
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
            # 範囲外のタスクはスキップ
            if end < min_date or start > max_date:
                continue
            start_pct = to_pct(start)
            width_pct = round(max(to_pct(end) - start_pct, 0.5), 2)
        else:
            if not (min_date <= start <= max_date):
                continue
            start_pct = to_pct(start)
            width_pct = None
        depth = getattr(task, 'tree_depth', 0)
        task_items.append({
            'task': task,
            'depth': depth,
            'margin_left': depth * 16,
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


def preprocess_description(project, _, form):
    # 時々エラーが発生しているようでリロードに時間がかかっているようなので
    # 一旦対応を削除
    # form.instance.description = re.sub(
    #         r'(commit:\s*([0-9a-zA-Z]+))', 
    #         f"[\g<1>]({project.git_url})", form.instance.description)
    # m_iter = re.finditer(r'\#([0-9]+)', form.instance.description)
    # form.instance.description = re.sub(
    #     r'\#([0-9]+)', 
    #     "[\#\g<1>](/task_app/tasks/\g<1>/)", 
    #     form.instance.description)
    # return list(filter(lambda item: item != None,
    #     map(lambda m: Task.objects.get(pk=m.group(1)), m_iter)))
    return []
        

class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "task_app/project_list.html"
    context_object_name = "projects"
    
    def get_queryset(self):
        return self.request.user.projects.all()
    
    
    def get_context_data(self, **kwargs) -> dict[str, any]:
        context = super().get_context_data(**kwargs)
        status_list = list(map(lambda status: f"status={status.pk}", Status.objects.filter(is_done=False)))
        context["status_filter"] = "&".join(status_list)
        active_status_list = Status.objects.filter(is_done=False)
        context["status_list"] = Status.objects.all()
        tasks_by_project = []
        for project in self.request.user.projects.order_by("name"):
            project_tasks = Task.objects.with_tree_fields().filter(
                status__in=active_status_list,
                assignee=self.request.user,
                project=project,
            )
            if project_tasks.exists():
                tasks_by_project.append((project, project_tasks))
        context["tasks_by_project"] = tasks_by_project
        context["watching_tasks"] = self.request.user.watches.all()

        # 最近更新されたタスク
        period = self.request.GET.get("period", "today")
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if period == "week":
            updated_filter = {"updated_at__gte": today_start - timedelta(days=7)}
        else:
            period = "today"
            updated_filter = {"updated_at__gte": today_start}

        accessible_tasks = Task.objects.filter(
            Q(project__participants=self.request.user) |
            Q(assignee=self.request.user)
        ).distinct().select_related("project", "status", "assignee")

        context["recently_updated_tasks"] = accessible_tasks.filter(**updated_filter).order_by("-updated_at")
        context["period"] = period

        gantt_from = _parse_gantt_date(self.request.GET.get('gantt_from'))
        gantt_to = _parse_gantt_date(self.request.GET.get('gantt_to'))
        context["gantt_from"] = self.request.GET.get('gantt_from', '')
        context["gantt_to"] = self.request.GET.get('gantt_to', '')

        gantt_by_project = []
        for project in self.request.user.projects.order_by("name"):
            gantt_by_project.append({'project': project, 'gantt': build_gantt_data(project, gantt_from, gantt_to)})
        context["gantt_by_project"] = gantt_by_project
        return context
    


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "task_app/project_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        return self.request.user.projects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_status_list = self.request.GET.getlist("status")
        
        status_list = list(map(lambda status: f"status={status.pk}", Status.objects.filter(is_done=False)))
        context["status_filter"] = "&".join(status_list)
        context["status_list"] = Status.objects.all()
        context["selected_status_list"] = list(map(lambda x: int(x), selected_status_list))
        context["tasks"] = self.object.task_set.filter(status__in=selected_status_list).prefetch_related(
            Prefetch(
                "tasks",
                queryset=Task.objects.filter(status__in=selected_status_list),
                to_attr="filtered_tasks",
            )
        )
        gantt_from = _parse_gantt_date(self.request.GET.get('gantt_from'))
        gantt_to = _parse_gantt_date(self.request.GET.get('gantt_to'))
        context["gantt_from"] = self.request.GET.get('gantt_from', '')
        context["gantt_to"] = self.request.GET.get('gantt_to', '')
        context["gantt"] = build_gantt_data(self.object, gantt_from, gantt_to)
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    fields = ["name", "git_url"]
    template_name = "task_app/project_form.html"
    
    def get_success_url(self):
        return reverse_lazy("project_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.user.projects.add(self.object)
        self.request.user.save()
        return response


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "task_app/project_form.html"

    def get_queryset(self):
        return self.request.user.projects.all()
    
    def get_success_url(self):
        return reverse_lazy("project_detail", kwargs={"pk": self.object.pk})


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project

    def get_queryset(self):
        return self.request.user.projects.all()
    
    def get_success_url(self):
        return reverse_lazy("project_list")

class StatusListView(LoginRequiredMixin, ListView):
    model = Status
    template_name = "task_app/status_list.html"
    context_object_name = "status_list"
    
    def get_success_url(self):
        return reverse_lazy("project_list")


class StatusDetailView(LoginRequiredMixin, DetailView):
    model = Status
    template_name = "task_app/status_detail.html"
    context_object_name = "status"

    def get_success_url(self):
        return reverse_lazy("project_list")

class StatusCreateView(LoginRequiredMixin, CreateView):
    model = Status
    fields = ["name", "is_done"]
    template_name = "task_app/status_form.html"

    def get_success_url(self):
        return reverse_lazy("project_list")

class StatusUpdateView(LoginRequiredMixin, UpdateView):
    model = Status
    fields = ["name", "is_done"]
    template_name = "task_app/status_form.html"

    def get_success_url(self):
        return reverse_lazy("project_list")

class StatusDeleteView(LoginRequiredMixin, DeleteView):
    model = Status

    def get_success_url(self):
        return reverse_lazy("project_list")

class CommentListView(LoginRequiredMixin, ListView):
    model = Comment
    template_name = "task_app/comment_list.html"
    context_object_name = "comments"

class CommentDetailView(LoginRequiredMixin, DetailView):
    model = Comment
    template_name = "task_app/comment_detail.html"
    context_object_name = "comment"

    def get_queryset(self):
        return Comment.objects.filter(
            Q(author=self.request.user) |
            Q(task__project__participants=self.request.user)
        ).distinct()


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = "task_app/comment_form.html"
    
    def get_initial(self):
        initial = super().get_initial()

        task = self.request.GET.get("task")
        if task:
            initial["task"] = task

        return initial
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("project_list")


class CommentUpdateView(LoginRequiredMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = "task_app/comment_form.html"

    def get_queryset(self):
        return Comment.objects.filter(
            Q(author=self.request.user) |
            Q(task__project__participants=self.request.user)
        ).distinct()
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("project_list")

class CommentDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment

    def get_queryset(self):
        return Comment.objects.filter(
            Q(author=self.request.user) |
            Q(task__project__participants=self.request.user)
        ).distinct()

    def get_success_url(self):
        return reverse_lazy("project_list")

class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "task_app/task_list.html"
    context_object_name = "tasks"
    
    def get_context_data(self, **kwargs) -> dict[str, any]:
        context = super().get_context_data(**kwargs)
        selected_status_list = self.request.GET.getlist("status")
        selected_status_ids = list(map(lambda x: int(x), selected_status_list))
        context["selected_status_list"] = selected_status_ids
        context["status_list"] = Status.objects.all()

        tasks = self.get_queryset()
        if selected_status_ids:
            tasks = tasks.filter(status__in=selected_status_ids)

        context["tasks"] = tasks
        return context

    def get_queryset(self):
        return Task.objects.with_tree_fields().annotate(
            completed_subtask_count=Count(
                'tasks',
                filter=Q(tasks__status__is_done=True),
                distinct=True,
            ),
            total_subtask_count=Count('tasks', distinct=True),
        )

class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "task_app/task_detail.html"

    def get_queryset(self):
        return Task.objects.filter(
            Q(project__participants=self.request.user) |
            Q(assignee=self.request.user)
        ).distinct()
    
    def get_context_data(self, **kwargs) -> dict[str, any]:
        context = super().get_context_data(**kwargs)
        selected_status_list = self.request.GET.getlist("status")
        context["selected_status_list"] = list(map(lambda x: int(x), selected_status_list))
        context["status_list"] = Status.objects.all()
        context["status_filter"] = "&".join(list(map(lambda status: f"status={status}", selected_status_list)))
        context["tasks"] = self.object.tasks.filter(
            status__in=selected_status_list)
        context["related_tasks"] = self.object.related_tasks.filter(
            status__in=selected_status_list)

        parent_objects = []
        current = self.object
        while current != None:
            parent_objects.insert(0, current)
            current = current.parent
        context["parent_objects"] = parent_objects
        
        return context


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "task_app/task_form.html"

    def _resolve_project(self):
        project_id = self.request.GET.get("project")
        task_id = self.request.GET.get("task")
        if project_id:
            return Project.objects.filter(
                pk=project_id, participants=self.request.user
            ).first()
        if task_id:
            parent_task = Task.objects.filter(
                Q(project__participants=self.request.user) |
                Q(assignee=self.request.user),
                pk=task_id,
            ).distinct().first()
            if parent_task:
                return parent_task.project
        return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['project'] = self._resolve_project()
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        project = self._resolve_project()
        task_id = self.request.GET.get("task")
        if project:
            initial["project"] = project.pk
        if task_id:
            initial["parent"] = task_id
        initial["assignee"] = self.request.user.pk
        return initial

    def form_valid(self, form):
        project_id = self.request.GET.get("project")
        task = self.request.GET.get("task")

        if project_id:
            project = Project.objects.filter(
                pk=project_id,
                participants=self.request.user
            ).first()
            if project:
                form.instance.project = project

        if task:
            parent_task = Task.objects.filter(
                Q(project__participants=self.request.user) |
                Q(assignee=self.request.user),
                pk=task,
            ).distinct().first()
            if parent_task:
                form.instance.parent = parent_task
                form.instance.project = parent_task.project

        form.instance.completed_at = timezone.now() \
            if form.instance.status.is_done else None
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("project_list")


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = "task_app/task_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['project'] = self.object.project
        return kwargs

    def get_queryset(self):
        return Task.objects.filter(
            Q(project__participants=self.request.user) |
            Q(assignee=self.request.user)
        ).distinct()
    
    def get_context_data(self, **kwargs):
        selected_status_list = self.request.GET.getlist("status")
        context = super().get_context_data(**kwargs)
        context["status_list"] = Status.objects.all()
        context["selected_status_list"] = list(map(lambda x: int(x), selected_status_list))
        context["tasks"] = self.object.tasks.filter(
            status__in=selected_status_list)
        return context

    def form_valid(self, form):
        form.instance.completed_at = timezone.now() \
            if form.instance.status.is_done else None
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("project_list")


class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task

    def get_queryset(self):
        return Task.objects.filter(
            Q(project__participants=self.request.user) |
            Q(assignee=self.request.user)
        ).distinct()
    
    def get_success_url(self):
        return reverse_lazy("project_list")


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = "task_app/signup.html" 
    success_url = reverse_lazy('project_list')

    def form_valid(self, form):
        user = form.save() # formの情報を保存
        login(self.request, user) # 認証
        self.object = user 
        return HttpResponseRedirect(self.get_success_url())


class TaskWatchView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        user = request.user
        pk = kwargs["pk"]
        task = Task.objects.filter(
            Q(project__participants=user) |
            Q(assignee=user),
            pk=pk,
        ).first()
        if task:
            user.watches.add(task)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("project_list")


class TaskUnwatchView(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        user = request.user
        pk = kwargs["pk"]
        task = Task.objects.filter(
            Q(project__participants=user) |
            Q(assignee=user),
            pk=pk,
        ).first()
        if task:
            user.watches.remove(task)
        return HttpResponseRedirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse_lazy("project_list")
