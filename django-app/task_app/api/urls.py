from rest_framework.routers import DefaultRouter
from .views import (
    ProjectViewSet, StatusViewSet, CommentViewSet, TagViewSet,
    TaskViewSet, UserPreferencesViewSet, RuleViewSet, TaskTypeViewSet,
    TaskTypeFieldViewSet, TaskFieldValueViewSet,
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet)
router.register(r'statuses', StatusViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'tags', TagViewSet)
router.register(r'tasks', TaskViewSet)
router.register(r'user-preferences', UserPreferencesViewSet)
router.register(r'rules', RuleViewSet)
router.register(r'task-types', TaskTypeViewSet)
router.register(r'task-type-fields', TaskTypeFieldViewSet)
router.register(r'task-field-values', TaskFieldValueViewSet)

urlpatterns = router.urls
