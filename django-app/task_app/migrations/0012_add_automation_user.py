from django.db import migrations


def add_automation_user(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserPreferences = apps.get_model('task_app', 'UserPreferences')
    user, created = User.objects.get_or_create(
        username='Automation',
        defaults={'is_active': False, 'email': ''},
    )
    if created:
        UserPreferences.objects.get_or_create(user=user)


class Migration(migrations.Migration):

    dependencies = [
        ('task_app', '0011_add_api_key_to_userpreferences'),
    ]

    operations = [
        migrations.RunPython(add_automation_user, migrations.RunPython.noop),
    ]
