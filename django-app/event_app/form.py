from django import forms
from task_app.models import Project
from .models import Event, EventStatus, Inventory, InventoryItemRelation, Item


class EventForm(forms.ModelForm):
    event_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    status = forms.ModelChoiceField(
        queryset=EventStatus.objects.none(),
        required=False,
        empty_label='（なし）',
        label='ステータス',
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['project'].queryset = Project.objects.filter(participants=user)
        if project is not None:
            self.fields['status'].queryset = EventStatus.objects.filter(project=project)
            self.fields['previous_event'].queryset = Event.objects.filter(project=project)
        else:
            self.fields['status'].queryset = EventStatus.objects.all()

    class Meta:
        model = Event
        fields = ['name', 'event_date', 'participant_count', 'project', 'previous_event', 'status']

class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = '__all__'

InventoryItemFormSet = forms.inlineformset_factory(
    Inventory,
    InventoryItemRelation,
    fields=("item", "case_count", "item_count"),
    extra=1)
