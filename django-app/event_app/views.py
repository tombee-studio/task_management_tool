from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.forms.models import model_to_dict
from .models import *
from .form import *

class EventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = "event_app/event_list.html"
    context_object_name = "Events"
    
    def get_queryset(self):
        return self.request.user.Events.all()


class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = "event_app/event_detail.html"


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "event_app/event_form.html"
    
    def get_success_url(self):
        return reverse_lazy("event_detail", kwargs={"pk": self.object.pk})
    
    def get_initial(self):
        initial = super().get_initial()
        pk = self.request.GET.get("previous", None)
        if pk != None:
          previous = Event.objects.get(pk=pk)
          initial.update(model_to_dict(previous))
          initial["previous_event"] = previous
        return initial


class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = "event_app/event_form.html"
    
    def get_success_url(self):
        return reverse_lazy("event_detail", kwargs={"pk": self.kwargs["pk"]})


class EventDeleteView(LoginRequiredMixin, DeleteView):
    model = Event
    
    def get_success_url(self):
        return reverse_lazy("event_list")


class InventoryListView(LoginRequiredMixin, ListView):
    model = Inventory
    template_name = "event_app/inventory_list.html"
    
    def get_queryset(self):
        return self.request.user.events.all()


class InventoryDetailView(LoginRequiredMixin, DetailView):
    model = Inventory
    template_name = "event_app/inventory_detail.html"
    
    def get_context_data(self, **kwargs) -> dict[str, any]:
        context = super().get_context_data(**kwargs)
        context["items"] = self.object.get_previous_difference()
        return context
    


class InventoryCreateView(LoginRequiredMixin, CreateView):
    model = Inventory
    form_class = InventoryForm
    template_name = "event_app/inventory_form.html"
    
    def get_success_url(self):
        return reverse_lazy("event_detail", kwargs={"pk": self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        pk = self.request.GET.get("previous", None)
        if pk != None:
          previous = Inventory.objects.get(pk=pk)
          initial.update(model_to_dict(previous))
          initial["name"] = ""
          initial["previous_inventory"] = previous
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context["formset"] = InventoryItemFormSet(self.request.POST)
        else:
            context["formset"] = InventoryItemFormSet(instance=Event())
        
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        formset = InventoryItemFormSet(self.request.POST)
        if formset.is_valid():
            formset.save()
        return response


class InventoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Inventory
    form_class = InventoryForm
    template_name = "event_app/inventory_form.html"
    
    def get_success_url(self):
        return reverse_lazy("event_detail", kwargs={"pk": self.kwargs["pk"]})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context["formset"] = InventoryItemFormSet(
                self.request.POST
            )
        else:
            context["formset"] = InventoryItemFormSet(instance=self.object)
        
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        formset = InventoryItemFormSet(
            self.request.POST, 
            instance=self.object)
        if formset.is_valid():
            formset.save()
        return response


class InventoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Inventory
    
    def get_success_url(self):
        return reverse_lazy("inventory_list")

