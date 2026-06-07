from django.db import migrations


def create_user_preferences(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserPreferences = apps.get_model('task_app', 'UserPreferences')
    for user in User.objects.all():
        UserPreferences.objects.get_or_create(user=user)


class Migration(migrations.Migration):

    dependencies = [
        ('task_app', '0008_widgetconfig'),
    ]

    operations = [
        migrations.RunPython(create_user_preferences, migrations.RunPython.noop),
    ]
