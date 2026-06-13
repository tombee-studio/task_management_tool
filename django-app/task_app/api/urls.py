from rest_framework.routers import DefaultRouter
from .views import (
    ProjectViewSet, StatusViewSet, CommentViewSet, TagViewSet,
    TaskViewSet, UserPreferencesViewSet, RuleViewSet,
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet)
router.register(r'statuses', StatusViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'tags', TagViewSet)
router.register(r'tasks', TaskViewSet)
router.register(r'user-preferences', UserPreferencesViewSet)
router.register(r'rules', RuleViewSet)

urlpatterns = router.urls
