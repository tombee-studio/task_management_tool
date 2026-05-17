from django.urls import re_path, path
from .views import *

urlpatterns = [
    path("events/", EventListView.as_view(), name="event_list"),
    re_path(r"^events/(?P<pk>\d+)/$", EventDetailView.as_view(), name="event_detail"),
    path("events/create/", EventCreateView.as_view(), name="event_create"),
    re_path(r"^events/(?P<pk>\d+)/edit/$", EventUpdateView.as_view(), name="event_update"),
    re_path(r"^events/(?P<pk>\d+)/delete/$", EventDeleteView.as_view(), name="event_delete"),
    path("inventory/", InventoryListView.as_view(), name="inventory_list"),
    re_path(r"^inventory/(?P<pk>\d+)/$", InventoryDetailView.as_view(), name="inventory_detail"),
    path("inventory/create/", InventoryCreateView.as_view(), name="inventory_create"),
    re_path(r"^inventory/(?P<pk>\d+)/edit/$", InventoryUpdateView.as_view(), name="inventory_update"),
    re_path(r"^inventory/(?P<pk>\d+)/delete/$", InventoryDeleteView.as_view(), name="inventory_delete"),
]
