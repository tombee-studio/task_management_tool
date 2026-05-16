from django.contrib import admin
from .models import *

class EventInventoryRelationInline(admin.TabularInline):
    model = Inventory.events.through
    extra = 1


class InventoryAdmin(admin.ModelAdmin):
    inlines = [EventInventoryRelationInline]


# Register your models here.
admin.site.register(Event)
admin.site.register(Inventory, InventoryAdmin)
