from django.urls import path
from .views import *

urlpatterns = [
    path("events/", EventListView.as_view(), name="event_list"),
    path("events/<int:pk>/", EventDetailView.as_view(), name="event_detail"),
    path("events/create/", EventCreateView.as_view(), name="event_create"),
    path("events/<int:pk>/edit/", EventUpdateView.as_view(), name="event_update"),
    path("events/<int:pk>/delete/", EventDeleteView.as_view(), name="event_delete"),
    path("inventory/", InventoryListView.as_view(), name="inventory_list"),
    path("inventory/<int:pk>/", InventoryDetailView.as_view(), name="inventory_detail"),
    path("inventory/create/", InventoryCreateView.as_view(), name="inventory_create"),
    path("inventory/<int:pk>/edit/", InventoryUpdateView.as_view(), name="inventory_update"),
    path("inventory/<int:pk>/delete/", InventoryDeleteView.as_view(), name="inventory_delete"),
]
