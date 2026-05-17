from django import forms
from .models import * 

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        exclude = ("inventory",)

EventInventoryFormSet = forms.inlineformset_factory(
    Event,
    EventInventoryRelation,
    fields=("inventory", "case_count", "item_count"),
    extra=1)
