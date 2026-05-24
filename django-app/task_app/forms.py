from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from .models import Project, Task, Comment


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

    class Meta:
        model = Task
        fields = ['title', 'description', 'progress_summary', 'status', 'deadline']
    
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
