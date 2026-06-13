from rest_framework import serializers
from event_app.models import EventStatus, Event, Inventory, Item, InventoryItemRelation


class EventStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventStatus
        fields = ['id', 'name', 'is_done', 'project', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            'id', 'name', 'event_date', 'participant_count',
            'project', 'status', 'previous_event', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = ['id', 'name', 'event', 'previous_inventory', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['id', 'company', 'name', 'count_per_case', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class InventoryItemRelationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItemRelation
        fields = ['id', 'item', 'inventory', 'case_count', 'item_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
