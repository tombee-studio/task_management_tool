from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import *


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "task_app/project_list.html"
    context_object_name = "projects"
    
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        status_list = list(map(lambda status: f"status={status.pk}", Status.objects.filter(is_done=False)))
        context["status_filter"] = "&".join(status_list)
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
        context["tasks"] = self.object.task_set.filter(
            status__in=selected_status_list)

        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    fields = ["name"]
    template_name = "task_app/project_form.html"
    success_url = reverse_lazy("project_list")


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    fields = ["name"]
    template_name = "task_app/project_form.html"
    success_url = reverse_lazy("project_list")


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    success_url = reverse_lazy("project_list")


class StatusListView(LoginRequiredMixin, ListView):
    model = Status
    template_name = "task_app/status_list.html"
    context_object_name = "status_list"


class StatusDetailView(LoginRequiredMixin, DetailView):
    model = Status
    template_name = "task_app/status_detail.html"
    context_object_name = "status"


class StatusCreateView(LoginRequiredMixin, CreateView):
    model = Status
    fields = ["name", "is_done"]
    template_name = "task_app/status_form.html"
    success_url = reverse_lazy("status_list")


class StatusUpdateView(LoginRequiredMixin, UpdateView):
    model = Status
    fields = ["name", "is_done"]
    template_name = "task_app/status_form.html"
    success_url = reverse_lazy("status_list")


class StatusDeleteView(LoginRequiredMixin, DeleteView):
    model = Status
    success_url = reverse_lazy("status_list")


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
    success_url = reverse_lazy("comment_list")
    
    def get_initial(self):
        initial = super().get_initial()

        task = self.request.GET.get("task")
        if task:
            initial["task"] = task

        return initial
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class CommentUpdateView(LoginRequiredMixin, UpdateView):
    model = Comment
    fields = ["description", "task"]
    template_name = "task_app/comment_form.html"
    success_url = reverse_lazy("comment_list")
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class CommentDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment
    success_url = reverse_lazy("comment_list")


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "task_app/task_list.html"
    context_object_name = "tasks"


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "task_app/task_detail.html"
    context_object_name = "task"
    
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        selected_status_list = self.request.GET.getlist("status")
        context["selected_status_list"] = list(map(lambda x: int(x), selected_status_list))
        context["status_list"] = Status.objects.all()
        context["tasks"] = self.object.tasks.filter(
            status__in=selected_status_list)
        return context
    


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    fields = "__all__"
    template_name = "task_app/task_form.html"
    success_url = reverse_lazy("task_list")
    
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
        return super().form_valid(form)


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    fields = "__all__"
    template_name = "task_app/task_form.html"
    success_url = reverse_lazy("task_list")
    
    def get_context_data(self, **kwargs):
        selected_status_list = self.request.GET.getlist("status")
        context = super().get_context_data(**kwargs)
        context["status_list"] = Status.objects.all()
        context["selected_status_list"] = list(map(lambda x: int(x), selected_status_list))
        context["tasks"] = self.object.tasks.filter(
            status__in=selected_status_list)
        return context


class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    success_url = reverse_lazy("task_list")
