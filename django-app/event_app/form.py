from django import forms
from .models import * 

class EventForm(forms.ModelForm):
    event_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = Event
        fields = '__all__'

class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = '__all__'

InventoryItemFormSet = forms.inlineformset_factory(
    Inventory,
    InventoryItemRelation,
    fields=("item", "case_count", "item_count"),
    extra=1)
