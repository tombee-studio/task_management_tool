from django.urls import re_path, path
from .views import (
    EventListView, EventDetailView, EventCreateView, EventUpdateView, EventDeleteView,
    EventStatusCreateView, EventStatusUpdateView, EventStatusDeleteView,
    InventoryListView, InventoryDetailView, InventoryCreateView, InventoryUpdateView, InventoryDeleteView,
)

urlpatterns = [
    path("events/", EventListView.as_view(), name="event_list"),
    re_path(r"^events/(?P<pk>\d+)/$", EventDetailView.as_view(), name="event_detail"),
    path("events/create/", EventCreateView.as_view(), name="event_create"),
    re_path(r"^events/(?P<pk>\d+)/edit/$", EventUpdateView.as_view(), name="event_update"),
    re_path(r"^events/(?P<pk>\d+)/delete/$", EventDeleteView.as_view(), name="event_delete"),
    re_path(r"^projects/(?P<project_pk>\d+)/event_statuses/create/$", EventStatusCreateView.as_view(), name="event_status_create"),
    re_path(r"^event_statuses/(?P<pk>\d+)/edit/$", EventStatusUpdateView.as_view(), name="event_status_update"),
    re_path(r"^event_statuses/(?P<pk>\d+)/delete/$", EventStatusDeleteView.as_view(), name="event_status_delete"),
    path("inventory/", InventoryListView.as_view(), name="inventory_list"),
    re_path(r"^inventory/(?P<pk>\d+)/$", InventoryDetailView.as_view(), name="inventory_detail"),
    path("inventory/create/", InventoryCreateView.as_view(), name="inventory_create"),
    re_path(r"^inventory/(?P<pk>\d+)/edit/$", InventoryUpdateView.as_view(), name="inventory_update"),
    re_path(r"^inventory/(?P<pk>\d+)/delete/$", InventoryDeleteView.as_view(), name="inventory_delete"),
]
