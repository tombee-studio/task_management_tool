from django.db import migrations


def add_automation_to_projects(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Project = apps.get_model('task_app', 'Project')
    automation = User.objects.filter(username='Automation').first()
    if automation:
        for project in Project.objects.all():
            project.participants.add(automation)


class Migration(migrations.Migration):

    dependencies = [
        ('task_app', '0013_add_task_reporter'),
    ]

    operations = [
        migrations.RunPython(add_automation_to_projects, migrations.RunPython.noop),
    ]
