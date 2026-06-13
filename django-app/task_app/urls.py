from django.urls import re_path, path
from .views import *

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('users/me/', UserDetailView.as_view(), name='user_detail'),
    path('users/me/regenerate-api-key/', RegenerateAPIKeyView.as_view(), name='regenerate_api_key'),
    path("projects/", ProjectListView.as_view(), name="project_list"),
    re_path(r"^projects/(?P<pk>\d+)/$", ProjectDetailView.as_view(), name="project_detail"),
    path("projects/create/", ProjectCreateView.as_view(), name="project_create"),
    re_path(r"^projects/(?P<pk>\d+)/edit/$", ProjectUpdateView.as_view(), name="project_update"),
    re_path(r"^projects/(?P<pk>\d+)/delete/$", ProjectDeleteView.as_view(), name="project_delete"),
    path("statuss/", StatusListView.as_view(), name="status_list"),
    re_path(r"^statuss/(?P<pk>\d+)/$", StatusDetailView.as_view(), name="status_detail"),
    re_path(r"^projects/(?P<project_pk>\d+)/statuss/create/$", StatusCreateView.as_view(), name="status_create"),
    re_path(r"^statuss/(?P<pk>\d+)/edit/$", StatusUpdateView.as_view(), name="status_update"),
    re_path(r"^statuss/(?P<pk>\d+)/delete/$", StatusDeleteView.as_view(), name="status_delete"),
    path("comments/", CommentListView.as_view(), name="comment_list"),
    re_path(r"^comments/(?P<pk>\d+)/$", CommentDetailView.as_view(), name="comment_detail"),
    path("comments/create/", CommentCreateView.as_view(), name="comment_create"),
    re_path(r"^comments/(?P<pk>\d+)/edit/$", CommentUpdateView.as_view(), name="comment_update"),
    re_path(r"^comments/(?P<pk>\d+)/delete/$", CommentDeleteView.as_view(), name="comment_delete"),
    re_path(r"^tasks/(?P<pk>\d+)/$", TaskDetailView.as_view(), name="task_detail"),
    path("tasks/create/", TaskCreateView.as_view(), name="task_create"),
    re_path(r"^tasks/(?P<pk>\d+)/edit/$", TaskUpdateView.as_view(), name="task_update"),
    re_path(r"^tasks/(?P<pk>\d+)/delete/$", TaskDeleteView.as_view(), name="task_delete"),
    re_path(r"^tasks/(?P<pk>\d+)/watch/$", TaskWatchView.as_view(), name="task_watch"),
    re_path(r"^tasks/(?P<pk>\d+)/unwatch/$", TaskUnwatchView.as_view(), name="task_unwatch"),
]
