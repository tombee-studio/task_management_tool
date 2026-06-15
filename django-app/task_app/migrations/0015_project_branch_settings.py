from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('task_app', '0014_add_automation_to_all_projects'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='dev_branch',
            field=models.CharField(blank=True, default='develop', max_length=100),
        ),
        migrations.AddField(
            model_name='project',
            name='release_branch',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='project',
            name='main_branch',
            field=models.CharField(blank=True, default='main', max_length=100),
        ),
    ]
