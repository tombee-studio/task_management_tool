from rest_framework import serializers
from django.contrib.auth import get_user_model
from task_app.models import Project, Status, Comment, Tag, Task, UserPreferences, Rule, TaskType, TaskTypeField

User = get_user_model()


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'git_url', 'dev_branch', 'release_branch', 'main_branch', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ['id', 'name', 'is_done', 'project', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'author', 'description', 'task', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'project', 'description', 'progress_summary',
            'assignee', 'reporter', 'parent', 'status', 'task_type', 'deadline',
            'completed_at', 'event', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreferences
        fields = ['id', 'user', 'config', 'api_key']
        read_only_fields = ['id', 'api_key']


class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rule
        fields = [
            'id', 'project', 'name', 'pattern', 'dsl_template', 'enabled',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaskTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskType
        fields = ['id', 'project', 'name', 'parent']
        read_only_fields = ['id']


class TaskTypeFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskTypeField
        fields = ['id', 'task_type', 'name', 'label', 'field_type', 'required', 'order']
        read_only_fields = ['id']
