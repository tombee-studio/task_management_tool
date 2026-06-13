from rest_framework.routers import DefaultRouter
from .views import (
    EventStatusViewSet, EventViewSet, InventoryViewSet,
    ItemViewSet, InventoryItemRelationViewSet,
)

router = DefaultRouter()
router.register(r'event-statuses', EventStatusViewSet)
router.register(r'events', EventViewSet)
router.register(r'inventories', InventoryViewSet)
router.register(r'items', ItemViewSet)
router.register(r'inventory-item-relations', InventoryItemRelationViewSet)

urlpatterns = router.urls
