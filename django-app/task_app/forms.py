from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from .models import Project, Task, Comment, Status
from event_app.models import Event


class SignUpForm(UserCreationForm):

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'git_url']


class TaskForm(forms.ModelForm):
    deadline = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    event = forms.ModelChoiceField(
        queryset=Event.objects.none(),
        required=False,
        empty_label='（なし）',
    )
    assignee = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=True,
        label='担当者',
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['event'].queryset = Event.objects.filter(
                project__participants=user
            ).order_by('-event_date')
        else:
            self.fields['event'].queryset = Event.objects.all().order_by('-event_date')
        if project is not None:
            self.fields['assignee'].queryset = project.participants.all()
            self.fields['status'].queryset = Status.objects.filter(project=project)
        else:
            self.fields['assignee'].queryset = User.objects.all()
            self.fields['status'].queryset = Status.objects.all()

    class Meta:
        model = Task
        fields = ['title', 'description', 'progress_summary', 'assignee', 'status', 'deadline', 'event']
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        
        # チェック：ステータスが完了状態に変更されようとしている場合
        # 新規タスク（pk なし）はサブタスクを持てないのでスキップ
        if status and status.is_done and self.instance.pk:
            # 未完了のサブタスクがあるか確認
            incomplete_subtasks = self.instance.tasks.filter(status__is_done=False)
            if incomplete_subtasks.exists():
                raise forms.ValidationError(
                    '子タスクが未完了のため、親タスクを完了状態にすることはできません。'
                )
        
        return cleaned_data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['description', 'task']
