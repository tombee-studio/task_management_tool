.PHONY: setup test schema

setup:
	git config core.hooksPath .githooks

test:
	cd django-app && DJANGO_SETTINGS_MODULE=task_management.test_settings python manage.py test task_app event_app --verbosity=1

schema:
	cd django-app && DJANGO_SETTINGS_MODULE=task_management.test_settings python manage.py spectacular --file ../docs/openapi.yaml --validate
