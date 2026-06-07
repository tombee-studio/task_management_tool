from django.db import migrations

DEFAULT_CONFIG = """\
pages:
  - name: project_list
    widgets:
      - title: 自分のタスク一覧
        rules:
          - table: task
            filter: "assignee=me status__is_done=False"
        type: table
        order:
          - task
      - title: ウォッチしているタスク一覧
        rules:
          - table: task
            source: watched_tasks
            filter: "status__is_done=False"
        type: table
        order:
          - task
  - name: project_detail
    widgets:
      - title: 未完了のイベント一覧
        rules:
          - table: event
            filter: "status__is_done=False"
        type: table
        order:
          - event
      - title: 未完了のタスク一覧
        rules:
          - table: task
            filter: "status__is_done=False"
        type: table
        order:
          - task
  - name: task_detail
    widgets:
      - title: 関連するイベント
        rules:
          - table: event
            source: task_event
        type: table
        order:
          - event
      - title: 関連タスク
        rules:
          - table: task
            source: related_tasks
        type: table
        order:
          - task
      - title: サブタスク（未完了）
        rules:
          - table: task
            source: subtasks
            filter: "status__is_done=False"
        type: table
        order:
          - task
"""


def apply_default_config(apps, schema_editor):
    UserPreferences = apps.get_model('task_app', 'UserPreferences')
    UserPreferences.objects.filter(config='').update(config=DEFAULT_CONFIG)


class Migration(migrations.Migration):

    dependencies = [
        ('task_app', '0009_userpreferences_initial_data'),
    ]

    operations = [
        migrations.RunPython(apply_default_config, migrations.RunPython.noop),
    ]
