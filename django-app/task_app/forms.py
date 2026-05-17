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


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['description', 'task']
