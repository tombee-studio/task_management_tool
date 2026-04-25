from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import *


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "task_app/project_list.html"
    context_object_name = "projects"


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "task_app/project_detail.html"
    context_object_name = "project"


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

