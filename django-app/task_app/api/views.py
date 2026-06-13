from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from task_app.models import Project, Status, Comment, Tag, Task, UserPreferences, Rule
from task_app.signals import generate_api_key
from .serializers import (
    ProjectSerializer, StatusSerializer, CommentSerializer, TagSerializer,
    TaskSerializer, UserPreferencesSerializer, RuleSerializer,
)


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer


class StatusViewSet(viewsets.ModelViewSet):
    queryset = Status.objects.all()
    serializer_class = StatusSerializer


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer


class UserPreferencesViewSet(viewsets.ModelViewSet):
    queryset = UserPreferences.objects.all()
    serializer_class = UserPreferencesSerializer

    @action(detail=True, methods=['post'], url_path='generate-api-key')
    def generate_api_key(self, request, pk=None):
        prefs = self.get_object()
        prefs.api_key = generate_api_key()
        prefs.save(update_fields=['api_key'])
        return Response({'api_key': prefs.api_key})


class RuleViewSet(viewsets.ModelViewSet):
    queryset = Rule.objects.all()
    serializer_class = RuleSerializer
