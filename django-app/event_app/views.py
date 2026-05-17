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
    
    def get_context_data(self, **kwargs) -> dict[str, any]:
        context = super().get_context_data(**kwargs)
        context["inventory"] = Event.get_previous_difference(event=self.object)
        return context


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "event_app/event_form.html"
    
    def get_success_url(self):
        return reverse_lazy("event_detail", kwargs={"pk": self.object.pk})
    
    def get_initial(self):
        initial = super().get_initial()
        pk = self.request.GET["previous"]
        if pk != None:
          previous = Event.objects.get(pk=pk)
          initial.update(model_to_dict(previous))
          initial["previous_event"] = previous
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context["formset"] = EventInventoryFormSet(
                self.request.POST
            )
        else:
            context["formset"] = EventInventoryFormSet(instance=Event())
        
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        formset = EventInventoryFormSet(self.request.POST)
        if formset.is_valid():
            formset.save()
        return response


class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = "event_app/event_form.html"
    
    def get_success_url(self):
        return reverse_lazy("event_detail", kwargs={"pk": self.kwargs["pk"]})

    def get_initial(self):
        initial = super().get_initial()
        initial["formset"] = EventInventoryFormSet(instance=self.object)
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context["formset"] = EventInventoryFormSet(
                self.request.POST
            )
        else:
            context["formset"] = EventInventoryFormSet(instance=self.object)
        
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        formset = EventInventoryFormSet(
            self.request.POST, 
            instance=self.object)
        if formset.is_valid():
            formset.save()
        return response


class EventDeleteView(LoginRequiredMixin, DeleteView):
    model = Event
    
    def get_success_url(self):
        return reverse_lazy("event_list")
