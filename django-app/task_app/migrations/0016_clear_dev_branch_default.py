from django.db import migrations, models


def clear_develop_default(apps, schema_editor):
    """Reset dev_branch='develop' to '' on projects where it was never explicitly set.

    Migration 0015 applied default='develop' to all existing projects. Since the
    new default is '' (empty), existing records get the same treatment as new ones:
    fall back to main_branch -> GitHub API default_branch.
    """
    Project = apps.get_model('task_app', 'Project')
    Project.objects.filter(dev_branch='develop').update(dev_branch='')


class Migration(migrations.Migration):

    dependencies = [
        ('task_app', '0015_project_branch_settings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='dev_branch',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.RunPython(clear_develop_default, migrations.RunPython.noop),
    ]
