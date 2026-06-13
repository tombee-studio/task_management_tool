from rest_framework import viewsets
from event_app.models import EventStatus, Event, Inventory, Item, InventoryItemRelation
from .serializers import (
    EventStatusSerializer, EventSerializer, InventorySerializer,
    ItemSerializer, InventoryItemRelationSerializer,
)


class EventStatusViewSet(viewsets.ModelViewSet):
    queryset = EventStatus.objects.all()
    serializer_class = EventStatusSerializer


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer


class InventoryItemRelationViewSet(viewsets.ModelViewSet):
    queryset = InventoryItemRelation.objects.all()
    serializer_class = InventoryItemRelationSerializer
