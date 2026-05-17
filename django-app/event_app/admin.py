from django.contrib import admin
from .models import *

class InventoryItemRelationInline(admin.TabularInline):
    model = Inventory.items.through
    extra = 1


class InventoryAdmin(admin.ModelAdmin):
    inlines = [InventoryItemRelationInline]


# Register your models here.
admin.site.register(Event)
admin.site.register(Inventory, InventoryAdmin)
admin.site.register(Item)
