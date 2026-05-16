from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from .models import *
from django.forms.models import model_to_dict

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
    fields = "__all__"
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

    def form_valid(self, form):
        return super().form_valid(form)


class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    fields = "__all__"
    template_name = "event_app/event_form.html"
    
    def get_success_url(self):
        return reverse_lazy("event_detail", kwargs={"pk": self.kwargs["pk"]})


class EventDeleteView(LoginRequiredMixin, DeleteView):
    model = Event
    
    def get_success_url(self):
        return reverse_lazy("event_list")
