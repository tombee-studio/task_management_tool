import re
import datetime
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.db.models import Prefetch
from .models import *

from django.contrib.auth import login
from django.http import HttpResponseRedirect
from .forms import SignUpForm


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
        context["tasks"] = Task.objects.filter(
            status__in=active_status_list, 
            assignee=self.request.user)\
                .prefetch_related(
                    Prefetch(
                        "tasks",
                        queryset=Task.objects.filter(
                            status__in=active_status_list, 
                            assignee=self.request.user),
                        to_attr="filtered_tasks",
                    ))
        context["watching_tasks"] = self.request.user.watches.all()
        return context
    


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "task_app/project_detail.html"
    context_object_name = "project"
    
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

        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    fields = "__all__"
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
    fields = "__all__"
    template_name = "task_app/project_form.html"
    
    def get_success_url(self):
        return reverse_lazy("project_detail", kwargs={"pk": self.kwargs["pk"]})


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    
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


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    fields = ["description", "task"]
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
    fields = ["description", "task"]
    template_name = "task_app/comment_form.html"
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("project_list")

class CommentDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment
    success_url = reverse_lazy("comment_list")

    def get_success_url(self):
        return reverse_lazy("project_list")

class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "task_app/task_list.html"
    context_object_name = "tasks"
    
    def get_context_data(self, **kwargs) -> dict[str, any]:
        context = super().get_context_data(**kwargs)
        selected_status_list = self.request.GET.getlist("status")
        context["selected_status_list"] = list(map(lambda x: int(x), selected_status_list))
        context["status_list"] = Status.objects.all()
        context["tasks"] = Task.objects.filter(status__in=selected_status_list).prefetch_related(
            Prefetch(
                "tasks",
                queryset=Task.objects.filter(status__in=selected_status_list),
                to_attr="filtered_tasks",
            )
        )
        return context

    def get_queryset(self):
        return Task.objects.with_tree_fields()

class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "task_app/task_detail.html"
    
    def get_context_data(self, **kwargs) -> dict[str, any]:
        context = super().get_context_data(**kwargs)
        context["object"] = self.object
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
    fields = "__all__"
    template_name = "task_app/task_form.html"
    
    def get_initial(self):
        initial = super().get_initial()

        project = self.request.GET.get("project")
        task = self.request.GET.get("task")
        initial["assignee"] = self.request.user
        if project:
            initial["project"] = project
        if task:
            initial["project"] = Task.objects.get(pk=task).project.pk
            initial["parent"] = task

        return initial
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.completed_at = datetime.datetime.now() \
            if form.instance.status.is_done else None
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("project_list")


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    fields = "__all__"
    template_name = "task_app/task_form.html"
    
    def get_context_data(self, **kwargs):
        selected_status_list = self.request.GET.getlist("status")
        context = super().get_context_data(**kwargs)
        context["status_list"] = Status.objects.all()
        context["selected_status_list"] = list(map(lambda x: int(x), selected_status_list))
        context["tasks"] = self.object.tasks.filter(
            status__in=selected_status_list)
        return context

    def form_valid(self, form):
        form.instance.completed_at = datetime.datetime.now() \
            if form.instance.status.is_done else None
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("project_list")


class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    
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


class TaskWatchView(View):
    def post(self, request, *args, **kwargs):
        user = User.objects.get(pk=request.user.pk)
        pk = kwargs["pk"]
        task = Task.objects.get(pk=pk)
        user.watches.add(task)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("project_list")


class TaskUnwatchView(View):

    def post(self, request, *args, **kwargs):
        user = User.objects.get(pk=request.user.pk)
        pk = kwargs["pk"]
        task = Task.objects.get(pk=pk)
        user.watches.remove(task)
        return HttpResponseRedirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse_lazy("project_list")
