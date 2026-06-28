from rest_framework import serializers
from django.contrib.auth import get_user_model
from task_app.models import Project, Status, Comment, Tag, Task, UserPreferences, Rule, TaskType, TaskTypeField, TaskFieldValue

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


class TaskFieldValueNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskFieldValue
        fields = ['id', 'field', 'value']
        read_only_fields = ['id']


class TaskSerializer(serializers.ModelSerializer):
    field_values = TaskFieldValueNestedSerializer(many=True, required=False)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'project', 'description', 'progress_summary',
            'assignee', 'reporter', 'parent', 'status', 'task_type', 'deadline',
            'completed_at', 'event', 'field_values', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        field_values = attrs.get('field_values')
        if field_values:
            task_type = attrs.get('task_type')
            if task_type is None and self.instance is not None:
                task_type = self.instance.task_type
            if task_type is None:
                raise serializers.ValidationError(
                    {'field_values': 'task_type must be set to provide field_values.'}
                )
            for item in field_values:
                field = item['field']
                if field.task_type_id != task_type.id:
                    raise serializers.ValidationError({
                        'field_values':
                            f'Field {field.id} does not belong to task_type {task_type.id}.'
                    })
        return attrs

    def create(self, validated_data):
        field_values = validated_data.pop('field_values', None)
        task = super().create(validated_data)
        if field_values:
            self._save_field_values(task, field_values)
        return task

    def update(self, instance, validated_data):
        field_values = validated_data.pop('field_values', None)
        task = super().update(instance, validated_data)
        if field_values is not None:
            self._save_field_values(task, field_values)
        return task

    def _save_field_values(self, task, field_values):
        for item in field_values:
            TaskFieldValue.objects.update_or_create(
                task=task, field=item['field'],
                defaults={'value': item.get('value', '')},
            )


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
        fields = ['id', 'project', 'name', 'parent', 'agent']
        read_only_fields = ['id']


class TaskTypeFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskTypeField
        fields = ['id', 'task_type', 'name', 'label', 'field_type', 'required', 'order']
        read_only_fields = ['id']


class TaskFieldValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskFieldValue
        fields = ['id', 'task', 'field', 'value']
        read_only_fields = ['id']
