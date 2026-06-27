from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q

from .models import Project, Task, Comment, Status, Tag, UserPreferences, TaskType
from event_app.models import Event


class SignUpForm(UserCreationForm):

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


# エージェント設定（agent フィールド）で利用できる API のヘルプ。
# プロジェクト編集画面で agent フィールドの help_text として表示する。
AGENT_API_HELP = (
    'エージェントスクリプト（Python）で利用できる API:\n'
    'ctx.clone_git_url() : リポジトリをクローンする（git操作の前に必須）\n'
    'ctx.get_task() : 現在のタスク情報を取得する\n'
    'ctx.get_kinds() : プロジェクトのタスク種別を取得する\n'
    'ctx.decide_strategy(task, kinds) : 実装方針を決定する\n'
    'ctx.get_modification_level() : 改修規模(SMALL/MIDDLE/LARGE)を判定する\n'
    'ctx.create_subtasks(strategy) : サブタスクを作成する\n'
    'ctx.branch(task) : 作業ブランチを作成・切り替えする\n'
    'ctx.run_agent(prompt) : 任意のプロンプトで改修を実行する\n'
    'ctx.push(task) : 実装・テスト・コミット・プッシュを行う\n'
    'ctx.gh_create_pr(task) : GitHub の PR を作成する\n'
    'ctx.post_comment(task, message) : タスクにコメントを投稿する\n'
    'ctx.change_assignee(assignee_id) : 担当者を変更する\n'
    'ctx.get_assignee() : reporter の ID を取得する\n'
    'SMALL / MIDDLE / LARGE : 改修規模を表す定数'
)


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'git_url', 'dev_branch', 'release_branch', 'main_branch', 'agent']
        widgets = {
            'dev_branch': forms.TextInput(attrs={'placeholder': 'develop'}),
            'release_branch': forms.TextInput(attrs={'placeholder': 'release'}),
            'main_branch': forms.TextInput(attrs={'placeholder': 'main'}),
            'agent': forms.Textarea(attrs={'rows': 6}),
        }
        labels = {
            'dev_branch': '開発ブランチ',
            'release_branch': 'リリースブランチ',
            'main_branch': 'メインブランチ',
            'agent': 'エージェント設定',
        }
        help_texts = {
            'agent': AGENT_API_HELP,
        }


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
    tags = forms.CharField(
        required=False,
        label='タグ',
        help_text='スペース区切りで複数指定できます（例: bug 重要 frontend）。存在しないタグは自動作成されます。',
        widget=forms.TextInput(attrs={'placeholder': 'bug 重要 frontend'}),
    )
    task_type = forms.ModelChoiceField(
        queryset=TaskType.objects.none(),
        required=True,
        label='種別',
        empty_label='（種別を選択）',
    )
    dsl = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'ASSIGN {task_id} TO {username}\nLINK {src_id} -> {dst_id}\nEVENT {task_id} {event_id}\nPARENT {child_id} -> {parent_id}',
        }),
        label='DSL（保存後実行）',
        help_text=(
            '保存後に実行するDSLコマンドを入力してください（DBには保存されません）。'
            ' PARENT {child_id} -> {parent_id} で子タスクの親を変更できます。'
        ),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial['tags'] = ' '.join(self.instance.tags.values_list('name', flat=True))
        if project is not None:
            self.fields['event'].queryset = Event.objects.filter(
                project=project,
            ).filter(
                Q(status__is_done=False) | Q(status__isnull=True)
            ).order_by('-event_date')
        elif user is not None:
            self.fields['event'].queryset = Event.objects.filter(
                project__participants=user,
            ).filter(
                Q(status__is_done=False) | Q(status__isnull=True)
            ).order_by('-event_date')
        else:
            self.fields['event'].queryset = Event.objects.filter(
                Q(status__is_done=False) | Q(status__isnull=True)
            ).order_by('-event_date')
        if project is not None:
            automation_qs = User.objects.filter(username='Automation')
            self.fields['assignee'].queryset = (project.participants.all() | automation_qs).distinct()
            self.fields['status'].queryset = Status.objects.filter(project=project)
            self.fields['task_type'].queryset = TaskType.objects.filter(project=project)
        else:
            self.fields['assignee'].queryset = User.objects.all()
            self.fields['status'].queryset = Status.objects.all()
            self.fields['task_type'].queryset = TaskType.objects.all()

    class Meta:
        model = Task
        fields = ['title', 'description', 'progress_summary', 'assignee', 'task_type', 'status', 'deadline', 'event']
    
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

    def save(self, commit=True):
        task = super().save(commit=commit)

        def _save_tags():
            tags_input = self.cleaned_data.get('tags', '')
            tag_names = [t for t in tags_input.split() if t]
            tag_objs = [Tag.objects.get_or_create(name=name)[0] for name in tag_names]
            task.tags.set(tag_objs)

        if commit:
            _save_tags()
        else:
            old_save_m2m = self.save_m2m
            def _new_save_m2m():
                old_save_m2m()
                _save_tags()
            self.save_m2m = _new_save_m2m

        return task


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']


class UserPreferencesForm(forms.ModelForm):
    class Meta:
        model = UserPreferences
        fields = ['config']
        widgets = {
            'config': forms.Textarea(attrs={'rows': 6}),
        }
        labels = {
            'config': 'Widget設定',
        }


class CommentForm(forms.ModelForm):
    dsl = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'ASSIGN {task_id} TO {username}\nLINK {src_id} -> {dst_id}\nEVENT {task_id} {event_id}\nPARENT {child_id} -> {parent_id}',
        }),
        label='DSL（保存後実行）',
        help_text=(
            '保存後に実行するDSLコマンドを入力してください（DBには保存されません）。'
            ' PARENT {child_id} -> {parent_id} で子タスクの親を変更できます。'
        ),
    )

    class Meta:
        model = Comment
        fields = ['description', 'task']
