from django.db import migrations, models
import auditlog.models


class Migration(migrations.Migration):

    dependencies = [
        ('task_app', '0002_alter_project_participants'),
    ]

    operations = [
        migrations.CreateModel(
            name='Rule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('pattern', models.TextField()),
                ('dsl_template', models.TextField()),
                ('enabled', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('history', models.TextField(null=True)),
                ('project', models.ForeignKey(on_delete=models.CASCADE, to='task_app.project')),
            ],
        ),
    ]
