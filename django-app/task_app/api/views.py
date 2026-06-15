from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, inline_serializer
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from task_app.models import Project, Status, Comment, Tag, Task, UserPreferences, Rule
from task_app.signals import generate_api_key
from .serializers import (
    ProjectSerializer, StatusSerializer, CommentSerializer, TagSerializer,
    TaskSerializer, UserPreferencesSerializer, RuleSerializer,
)


@extend_schema_view(
    list=extend_schema(summary='List projects', tags=['Projects']),
    create=extend_schema(summary='Create a project', tags=['Projects']),
    retrieve=extend_schema(summary='Retrieve a project', tags=['Projects']),
    update=extend_schema(summary='Update a project', tags=['Projects']),
    partial_update=extend_schema(summary='Partially update a project', tags=['Projects']),
    destroy=extend_schema(summary='Delete a project', tags=['Projects']),
)
class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer


@extend_schema_view(
    list=extend_schema(summary='List statuses', tags=['Statuses']),
    create=extend_schema(summary='Create a status', tags=['Statuses']),
    retrieve=extend_schema(summary='Retrieve a status', tags=['Statuses']),
    update=extend_schema(summary='Update a status', tags=['Statuses']),
    partial_update=extend_schema(summary='Partially update a status', tags=['Statuses']),
    destroy=extend_schema(summary='Delete a status', tags=['Statuses']),
)
class StatusViewSet(viewsets.ModelViewSet):
    queryset = Status.objects.all()
    serializer_class = StatusSerializer


@extend_schema_view(
    list=extend_schema(summary='List comments', tags=['Comments']),
    create=extend_schema(summary='Create a comment', tags=['Comments']),
    retrieve=extend_schema(summary='Retrieve a comment', tags=['Comments']),
    update=extend_schema(summary='Update a comment', tags=['Comments']),
    partial_update=extend_schema(summary='Partially update a comment', tags=['Comments']),
    destroy=extend_schema(summary='Delete a comment', tags=['Comments']),
)
class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        task_id = self.request.query_params.get('task')
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs


@extend_schema_view(
    list=extend_schema(summary='List tags', tags=['Tags']),
    create=extend_schema(summary='Create a tag', tags=['Tags']),
    retrieve=extend_schema(summary='Retrieve a tag', tags=['Tags']),
    update=extend_schema(summary='Update a tag', tags=['Tags']),
    partial_update=extend_schema(summary='Partially update a tag', tags=['Tags']),
    destroy=extend_schema(summary='Delete a tag', tags=['Tags']),
)
class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


@extend_schema_view(
    list=extend_schema(summary='List tasks', tags=['Tasks']),
    create=extend_schema(summary='Create a task', tags=['Tasks']),
    retrieve=extend_schema(summary='Retrieve a task', tags=['Tasks']),
    update=extend_schema(summary='Update a task', tags=['Tasks']),
    partial_update=extend_schema(summary='Partially update a task', tags=['Tasks']),
    destroy=extend_schema(summary='Delete a task', tags=['Tasks']),
)
class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer


@extend_schema_view(
    list=extend_schema(summary='List user preferences', tags=['User Preferences']),
    create=extend_schema(summary='Create user preferences', tags=['User Preferences']),
    retrieve=extend_schema(summary='Retrieve user preferences', tags=['User Preferences']),
    update=extend_schema(summary='Update user preferences', tags=['User Preferences']),
    partial_update=extend_schema(summary='Partially update user preferences', tags=['User Preferences']),
    destroy=extend_schema(summary='Delete user preferences', tags=['User Preferences']),
)
class UserPreferencesViewSet(viewsets.ModelViewSet):
    queryset = UserPreferences.objects.all()
    serializer_class = UserPreferencesSerializer

    @extend_schema(
        summary='Generate a new API key',
        tags=['User Preferences'],
        request=None,
        responses={200: inline_serializer(
            name='ApiKeyResponse',
            fields={'api_key': serializers.CharField()},
        )},
    )
    @action(detail=True, methods=['post'], url_path='generate-api-key')
    def generate_api_key(self, request, pk=None):
        prefs = self.get_object()
        prefs.api_key = generate_api_key()
        prefs.save(update_fields=['api_key'])
        return Response({'api_key': prefs.api_key})


@extend_schema_view(
    list=extend_schema(summary='List rules', tags=['Rules']),
    create=extend_schema(summary='Create a rule', tags=['Rules']),
    retrieve=extend_schema(summary='Retrieve a rule', tags=['Rules']),
    update=extend_schema(summary='Update a rule', tags=['Rules']),
    partial_update=extend_schema(summary='Partially update a rule', tags=['Rules']),
    destroy=extend_schema(summary='Delete a rule', tags=['Rules']),
)
class RuleViewSet(viewsets.ModelViewSet):
    queryset = Rule.objects.all()
    serializer_class = RuleSerializer
