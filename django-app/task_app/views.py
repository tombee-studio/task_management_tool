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
from django.http import Http404, HttpResponseRedirect
from .forms import SignUpForm, ProjectForm, TaskForm, CommentForm, UserUpdateForm, UserPreferencesForm
from .models import UserPreferences
from .filters import TaskFilterMixin, apply_task_filters
from .dsl import execute_dsl
from .gantt import build_gantt_data
from .widget_loader import get_page_widgets, resolve_widget_data


def _parse_gantt_date(value):
    """GET パラメータの文字列を date に変換。不正値は None を返す。"""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


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
        

class ProjectListView(LoginRequiredMixin, TaskFilterMixin, ListView):
    model = Project
    template_name = "task_app/project_list.html"
    context_object_name = "projects"

    GANTT_FILTER_DEFAULT = 'status__is_done=False assignee=me'

    def get_queryset(self):
        return self.request.user.projects.all()

    def get_context_data(self, **kwargs) -> dict[str, any]:
        context = super().get_context_data(**kwargs)

        # --- ガントチャート（search_gantt パラメータ）---
        gantt_raw = self.get_filter_raw('search_gantt', self.GANTT_FILTER_DEFAULT)
        gantt_parsed = self.get_parsed_filters('search_gantt', self.GANTT_FILTER_DEFAULT)
        context['gantt_filter_value'] = gantt_raw

        assignee_val = gantt_parsed.get('assignee')
        if assignee_val is not None:
            try:
                gantt_assignee_ids = [int(assignee_val)]
            except (ValueError, TypeError):
                gantt_assignee_ids = [self.request.user.id]
        else:
            gantt_assignee_ids = None

        status_val = gantt_parsed.get('status__is_done')
        if status_val is not None:
            is_done = status_val.lower() not in ('false', '0', 'no')
            gantt_status = 'done' if is_done else 'active'
        else:
            gantt_status = 'all'

        gantt_by_project = []
        for project in self.request.user.projects.order_by("name"):
            gantt_by_project.append({'project': project, 'gantt': build_gantt_data(project, assignee_ids=gantt_assignee_ids, status_filter=gantt_status)})
        context["gantt_by_project"] = gantt_by_project

        user_preferences, _ = UserPreferences.objects.get_or_create(user=self.request.user)
        widget_configs = get_page_widgets(user_preferences.config, 'project_list')
        context["page_widgets"] = [
            resolve_widget_data(w, self.request.user)
            for w in widget_configs
        ]
        return context
    


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "task_app/project_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        return self.request.user.projects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user_preferences, _ = UserPreferences.objects.get_or_create(user=self.request.user)
        context["user_preferences"] = user_preferences

        context["status_list"] = self.object.statuses.all()
        context["task_type_list"] = self.object.task_types.all()

        gantt_from = _parse_gantt_date(self.request.GET.get('gantt_from'))
        gantt_to = _parse_gantt_date(self.request.GET.get('gantt_to'))
        context["gantt_from"] = self.request.GET.get('gantt_from', '')
        context["gantt_to"] = self.request.GET.get('gantt_to', '')

        gantt_assignees_raw = self.request.GET.get('gantt_assignees', '').strip()
        if gantt_assignees_raw:
            usernames = [u.strip() for u in re.split(r'[,\s]+', gantt_assignees_raw) if u.strip()]
            assignee_ids = list(User.objects.filter(username__in=usernames).values_list('id', flat=True))
        else:
            assignee_ids = [self.request.user.id]
        context["gantt_assignees"] = gantt_assignees_raw

        gantt_status = self.request.GET.get('gantt_status', 'active')
        if gantt_status not in ('active', 'all', 'done'):
            gantt_status = 'active'
        context["gantt_status"] = gantt_status

        context["gantt"] = build_gantt_data(self.object, gantt_from, gantt_to, assignee_ids=assignee_ids, status_filter=gantt_status)

        event_statuses = self.object.event_statuses.all()
        active_event_statuses = event_statuses.filter(is_done=False)
        selected_event_status_list = self.request.GET.getlist("event_status")
        if not selected_event_status_list:
            selected_event_status_list = [str(s.pk) for s in active_event_statuses]
        context["event_status_list"] = event_statuses
        context["selected_event_status_list"] = list(map(int, selected_event_status_list))

        widget_configs = get_page_widgets(user_preferences.config, 'project_detail')
        context["page_widgets"] = [
            resolve_widget_data(w, self.request.user, project=self.object)
            for w in widget_configs
        ]

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

    def get_queryset(self):
        project_pk = self.request.GET.get('project')
        if project_pk:
            return Status.objects.filter(project_id=project_pk)
        return Status.objects.filter(project__participants=self.request.user).distinct()


class StatusDetailView(LoginRequiredMixin, DetailView):
    model = Status
    template_name = "task_app/status_detail.html"
    context_object_name = "status"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context


class StatusCreateView(LoginRequiredMixin, CreateView):
    model = Status
    fields = ["name", "is_done"]
    template_name = "task_app/status_form.html"

    def _get_project(self):
        pk = self.kwargs.get('project_pk')
        if pk:
            return Project.objects.filter(pk=pk, participants=self.request.user).first()
        return None

    def dispatch(self, request, *args, **kwargs):
        if self._get_project() is None:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self._get_project()
        return context

    def form_valid(self, form):
        form.instance.project = self._get_project()
        return super().form_valid(form)

    def get_success_url(self):
        if self.object.project_id:
            return reverse_lazy("project_detail", kwargs={"pk": self.object.project_id}) + "#tab-status"
        return reverse_lazy("project_list")


class StatusUpdateView(LoginRequiredMixin, UpdateView):
    model = Status
    fields = ["name", "is_done"]
    template_name = "task_app/status_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context

    def get_success_url(self):
        if self.object.project_id:
            return reverse_lazy("project_detail", kwargs={"pk": self.object.project_id}) + "#tab-status"
        return reverse_lazy("project_list")


class StatusDeleteView(LoginRequiredMixin, DeleteView):
    model = Status

    def get_success_url(self):
        project_id = self.object.project_id
        if project_id:
            return reverse_lazy("project_detail", kwargs={"pk": project_id}) + "#tab-status"
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
        self.object = form.save()
        dsl_text = form.cleaned_data.get('dsl', '').strip()
        if dsl_text:
            execute_dsl(dsl_text)
        return HttpResponseRedirect(self.get_success_url())

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
        self.object = form.save()
        dsl_text = form.cleaned_data.get('dsl', '').strip()
        if dsl_text:
            execute_dsl(dsl_text)
        return HttpResponseRedirect(self.get_success_url())

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

        parent_objects = []
        current = self.object
        while current != None:
            parent_objects.insert(0, current)
            current = current.parent
        context["parent_objects"] = parent_objects

        user_preferences, _ = UserPreferences.objects.get_or_create(user=self.request.user)
        config = user_preferences.config or ''
        from .widget_loader import get_page_widgets, resolve_widget_data as _resolve
        widget_configs = get_page_widgets(config, 'task_detail')
        context["page_widgets"] = [
            _resolve(w, self.request.user, project=self.object.project, task=self.object)
            for w in widget_configs
        ]

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

        form.instance.reporter = self.request.user
        form.instance.completed_at = timezone.now() \
            if form.instance.status.is_done else None
        self.object = form.save()
        dsl_text = form.cleaned_data.get('dsl', '').strip()
        if dsl_text:
            execute_dsl(dsl_text)
        return HttpResponseRedirect(self.get_success_url())

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
        self.object = form.save()
        dsl_text = form.cleaned_data.get('dsl', '').strip()
        if dsl_text:
            execute_dsl(dsl_text)
        return HttpResponseRedirect(self.get_success_url())

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


class UserDetailView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'task_app/user_detail.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_preferences, _ = UserPreferences.objects.get_or_create(user=self.request.user)
        if 'preferences_form' not in context:
            context['preferences_form'] = UserPreferencesForm(instance=user_preferences)
        context['user_preferences'] = user_preferences
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        user_form = UserUpdateForm(request.POST, instance=self.object)
        user_preferences, _ = UserPreferences.objects.get_or_create(user=self.object)
        preferences_form = UserPreferencesForm(request.POST, instance=user_preferences)
        if user_form.is_valid() and preferences_form.is_valid():
            user_form.save()
            preferences_form.save()
            return HttpResponseRedirect(self.get_success_url())
        return self.render_to_response(self.get_context_data(
            form=user_form,
            preferences_form=preferences_form,
        ))

    def get_success_url(self):
        return reverse_lazy('user_detail')


class RegenerateAPIKeyView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        from .signals import generate_api_key
        prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
        prefs.api_key = generate_api_key()
        prefs.save(update_fields=['api_key'])
        return HttpResponseRedirect(reverse_lazy('user_detail'))


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = "task_app/signup.html" 
    success_url = reverse_lazy('project_list')

    def form_valid(self, form):
        user = form.save() # formの情報を保存
        login(self.request, user) # 認証
        self.object = user 
        return HttpResponseRedirect(self.get_success_url())


class TaskTypeCreateView(LoginRequiredMixin, CreateView):
    model = TaskType
    fields = ["name", "parent"]
    template_name = "task_app/task_type_form.html"

    def _get_project(self):
        pk = self.kwargs.get('project_pk')
        if pk:
            return Project.objects.filter(pk=pk, participants=self.request.user).first()
        return None

    def dispatch(self, request, *args, **kwargs):
        if self._get_project() is None:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        project = self._get_project()
        form.fields['parent'].queryset = TaskType.objects.filter(project=project)
        form.fields['parent'].required = False
        form.fields['parent'].empty_label = '（なし）'
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self._get_project()
        return context

    def form_valid(self, form):
        form.instance.project = self._get_project()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("project_detail", kwargs={"pk": self.object.project_id}) + "#tab-task-type"


class TaskTypeUpdateView(LoginRequiredMixin, UpdateView):
    model = TaskType
    fields = ["name", "parent"]
    template_name = "task_app/task_type_form.html"

    def get_queryset(self):
        return TaskType.objects.filter(project__participants=self.request.user)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['parent'].queryset = TaskType.objects.filter(
            project=self.object.project
        ).exclude(pk=self.object.pk)
        form.fields['parent'].required = False
        form.fields['parent'].empty_label = '（なし）'
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context

    def get_success_url(self):
        return reverse_lazy("project_detail", kwargs={"pk": self.object.project_id}) + "#tab-task-type"


class TaskTypeDeleteView(LoginRequiredMixin, DeleteView):
    model = TaskType
    template_name = "task_app/task_type_confirm_delete.html"

    def get_queryset(self):
        return TaskType.objects.filter(project__participants=self.request.user)

    def get_success_url(self):
        return reverse_lazy("project_detail", kwargs={"pk": self.object.project_id}) + "#tab-task-type"


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
