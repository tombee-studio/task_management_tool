from django.urls import path
from .views import *

urlpatterns = [
    path("projects/", ProjectListView.as_view(), name="project_list"),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="project_detail"),
    path("projects/create/", ProjectCreateView.as_view(), name="project_create"),
    path("projects/<int:pk>/edit/", ProjectUpdateView.as_view(), name="project_update"),
    path("projects/<int:pk>/delete/", ProjectDeleteView.as_view(), name="project_delete"),
    path("statuss/", StatusListView.as_view(), name="status_list"),
    path("statuss/<int:pk>/", StatusDetailView.as_view(), name="status_detail"),
    path("statuss/create/", StatusCreateView.as_view(), name="status_create"),
    path("statuss/<int:pk>/edit/", StatusUpdateView.as_view(), name="status_update"),
    path("statuss/<int:pk>/delete/", StatusDeleteView.as_view(), name="status_delete"),
    path("comments/", CommentListView.as_view(), name="comment_list"),
    path("comments/<int:pk>/", CommentDetailView.as_view(), name="comment_detail"),
    path("comments/create/", CommentCreateView.as_view(), name="comment_create"),
    path("comments/<int:pk>/edit/", CommentUpdateView.as_view(), name="comment_update"),
    path("comments/<int:pk>/delete/", CommentDeleteView.as_view(), name="comment_delete"),
]
