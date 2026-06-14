from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from event_app.models import EventStatus, Event, Inventory, Item, InventoryItemRelation
from .serializers import (
    EventStatusSerializer, EventSerializer, InventorySerializer,
    ItemSerializer, InventoryItemRelationSerializer,
)


@extend_schema_view(
    list=extend_schema(summary='List event statuses', tags=['Event Statuses']),
    create=extend_schema(summary='Create an event status', tags=['Event Statuses']),
    retrieve=extend_schema(summary='Retrieve an event status', tags=['Event Statuses']),
    update=extend_schema(summary='Update an event status', tags=['Event Statuses']),
    partial_update=extend_schema(summary='Partially update an event status', tags=['Event Statuses']),
    destroy=extend_schema(summary='Delete an event status', tags=['Event Statuses']),
)
class EventStatusViewSet(viewsets.ModelViewSet):
    queryset = EventStatus.objects.all()
    serializer_class = EventStatusSerializer


@extend_schema_view(
    list=extend_schema(summary='List events', tags=['Events']),
    create=extend_schema(summary='Create an event', tags=['Events']),
    retrieve=extend_schema(summary='Retrieve an event', tags=['Events']),
    update=extend_schema(summary='Update an event', tags=['Events']),
    partial_update=extend_schema(summary='Partially update an event', tags=['Events']),
    destroy=extend_schema(summary='Delete an event', tags=['Events']),
)
class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


@extend_schema_view(
    list=extend_schema(summary='List inventories', tags=['Inventories']),
    create=extend_schema(summary='Create an inventory', tags=['Inventories']),
    retrieve=extend_schema(summary='Retrieve an inventory', tags=['Inventories']),
    update=extend_schema(summary='Update an inventory', tags=['Inventories']),
    partial_update=extend_schema(summary='Partially update an inventory', tags=['Inventories']),
    destroy=extend_schema(summary='Delete an inventory', tags=['Inventories']),
)
class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer


@extend_schema_view(
    list=extend_schema(summary='List items', tags=['Items']),
    create=extend_schema(summary='Create an item', tags=['Items']),
    retrieve=extend_schema(summary='Retrieve an item', tags=['Items']),
    update=extend_schema(summary='Update an item', tags=['Items']),
    partial_update=extend_schema(summary='Partially update an item', tags=['Items']),
    destroy=extend_schema(summary='Delete an item', tags=['Items']),
)
class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer


@extend_schema_view(
    list=extend_schema(summary='List inventory-item relations', tags=['Inventory Items']),
    create=extend_schema(summary='Create an inventory-item relation', tags=['Inventory Items']),
    retrieve=extend_schema(summary='Retrieve an inventory-item relation', tags=['Inventory Items']),
    update=extend_schema(summary='Update an inventory-item relation', tags=['Inventory Items']),
    partial_update=extend_schema(summary='Partially update an inventory-item relation', tags=['Inventory Items']),
    destroy=extend_schema(summary='Delete an inventory-item relation', tags=['Inventory Items']),
)
class InventoryItemRelationViewSet(viewsets.ModelViewSet):
    queryset = InventoryItemRelation.objects.all()
    serializer_class = InventoryItemRelationSerializer
