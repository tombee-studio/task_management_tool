from django.http import Http404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.forms.models import model_to_dict
from task_app.models import Project
from .models import Event, EventStatus, Inventory, InventoryItemRelation, Item
from .form import EventForm, InventoryForm, InventoryItemFormSet

class EventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = "event_app/event_list.html"
    context_object_name = "Events"
    
    def get_queryset(self):
        return Event.objects.filter(project__participants=self.request.user)


class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = "event_app/event_detail.html"

    def get_queryset(self):
        return Event.objects.filter(project__participants=self.request.user)


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "event_app/event_form.html"

    def _get_project(self):
        project_id = self.request.GET.get('project')
        if project_id:
            return Project.objects.filter(pk=project_id, participants=self.request.user).first()
        return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['project'] = self._get_project()
        return kwargs

    def get_success_url(self):
        return reverse_lazy("event_detail", kwargs={"pk": self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        project = self._get_project()
        if project is not None:
            initial["project"] = project
        pk = self.request.GET.get("previous", None)
        if pk is not None:
            previous = Event.objects.get(pk=pk)
            initial.update(model_to_dict(previous))
            initial["previous_event"] = previous
        return initial


class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = "event_app/event_form.html"

    def get_queryset(self):
        return Event.objects.filter(project__participants=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['project'] = self.object.project
        return kwargs

    def get_success_url(self):
        return reverse_lazy("event_detail", kwargs={"pk": self.object.pk})


class EventDeleteView(LoginRequiredMixin, DeleteView):
    model = Event

    def get_queryset(self):
        return Event.objects.filter(project__participants=self.request.user)
    
    def get_success_url(self):
        return reverse_lazy("event_list")


class InventoryListView(LoginRequiredMixin, ListView):
    model = Inventory
    template_name = "event_app/inventory_list.html"
    
    def get_queryset(self):
        return Inventory.objects.filter(event__project__participants=self.request.user)


class InventoryDetailView(LoginRequiredMixin, DetailView):
    model = Inventory
    template_name = "event_app/inventory_detail.html"

    def get_queryset(self):
        return Inventory.objects.filter(event__project__participants=self.request.user)
    
    def get_context_data(self, **kwargs) -> dict[str, any]:
        context = super().get_context_data(**kwargs)
        context["items"] = self.object.get_previous_difference()
        return context
    


class InventoryCreateView(LoginRequiredMixin, CreateView):
    model = Inventory
    form_class = InventoryForm
    template_name = "event_app/inventory_form.html"
    
    def get_success_url(self):
        return reverse_lazy("inventory_detail", kwargs={"pk": self.object.pk})

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

    def get_queryset(self):
        return Inventory.objects.filter(event__project__participants=self.request.user)
    
    def get_success_url(self):
        return reverse_lazy("inventory_detail", kwargs={"pk": self.object.pk})
    
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

    def get_queryset(self):
        return Inventory.objects.filter(event__project__participants=self.request.user)

    def get_success_url(self):
        return reverse_lazy("inventory_list")


# ---------------------------------------------------------------------------
# EventStatus CRUD
# ---------------------------------------------------------------------------

class EventStatusCreateView(LoginRequiredMixin, CreateView):
    model = EventStatus
    fields = ['name', 'is_done']
    template_name = "event_app/event_status_form.html"

    def _get_project(self):
        pk = self.kwargs.get('project_pk')
        if pk:
            return Project.objects.filter(pk=pk, participants=self.request.user).first()
        return None

    def dispatch(self, request, *args, **kwargs):
        if self._get_project() is None:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self._get_project()
        return context

    def form_valid(self, form):
        form.instance.project = self._get_project()
        return super().form_valid(form)

    def get_success_url(self):
        if self.object.project_id:
            return reverse_lazy("project_detail", kwargs={"pk": self.object.project_id}) + "#tab-event-status"
        return reverse_lazy("project_list")


class EventStatusUpdateView(LoginRequiredMixin, UpdateView):
    model = EventStatus
    fields = ['name', 'is_done']
    template_name = "event_app/event_status_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        return context

    def get_success_url(self):
        if self.object.project_id:
            return reverse_lazy("project_detail", kwargs={"pk": self.object.project_id}) + "#tab-event-status"
        return reverse_lazy("project_list")


class EventStatusDeleteView(LoginRequiredMixin, DeleteView):
    model = EventStatus

    def get_success_url(self):
        project_id = self.object.project_id
        if project_id:
            return reverse_lazy("project_detail", kwargs={"pk": project_id}) + "#tab-event-status"
        return reverse_lazy("project_list")

