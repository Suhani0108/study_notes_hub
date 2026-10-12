import os

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView,
)
from django.views.generic.detail import SingleObjectMixin

from .forms import NoteForm, SubjectForm
from .models import Note, Subject


# ---------- Reusable mixins ----------

class OwnerMixin(LoginRequiredMixin):
    """Login required, and only the logged-in user's objects are visible.

    DetailView/UpdateView/DeleteView look objects up through get_queryset(),
    so asking for someone else's object gives a 404 (not found).
    """

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class UserFormMixin:
    """Passes the logged-in user into the form (our forms need it)."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class DeleteMessageMixin:
    """Shows a success message after deleting, e.g. 'Biology' deleted."""

    def form_valid(self, form):
        messages.success(self.request, f'"{self.object}" was deleted.')
        return super().form_valid(form)


# ---------- Dashboard ----------

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'notes/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['subject_count'] = user.subjects.count()
        context['note_count'] = user.notes.count()
        context['recent_notes'] = user.notes.select_related('subject')[:5]
        return context


# ---------- Subjects ----------

class SubjectListView(OwnerMixin, ListView):
    model = Subject
    paginate_by = 12

    def get_queryset(self):
        # note_count is a new attribute on each subject: how many notes it has.
        # annotate() drops the model's default ordering, so order explicitly.
        return super().get_queryset().annotate(note_count=Count('notes')).order_by('name')


class SubjectDetailView(OwnerMixin, DetailView):
    model = Subject


class SubjectCreateView(LoginRequiredMixin, UserFormMixin, SuccessMessageMixin, CreateView):
    model = Subject
    form_class = SubjectForm
    success_message = 'Subject "%(name)s" was created.'  # filled in from the form data


class SubjectUpdateView(OwnerMixin, UserFormMixin, SuccessMessageMixin, UpdateView):
    model = Subject
    form_class = SubjectForm
    success_message = 'Subject "%(name)s" was updated.'


class SubjectDeleteView(OwnerMixin, DeleteMessageMixin, DeleteView):
    model = Subject
    success_url = reverse_lazy('subject_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        count = self.object.notes.count()
        if count:
            # CASCADE deletes the notes too, so warn the user first
            context['warning'] = f'Its {count} note(s) and their PDFs will be deleted too.'
        return context


# ---------- Notes ----------

class NoteListView(OwnerMixin, ListView):
    model = Note
    paginate_by = 10

    def get_queryset(self):
        notes = super().get_queryset().select_related('subject')

        # Search: /notes/?q=mitosis matches the title OR the content.
        # Q objects let us combine conditions with | (or) and & (and).
        self.query = self.request.GET.get('q', '').strip()
        if self.query:
            notes = notes.filter(Q(title__icontains=self.query) | Q(content__icontains=self.query))

        # Filter by subject: /notes/?subject=3 (works together with search)
        self.subject_id = self.request.GET.get('subject', '')
        if self.subject_id.isdigit():
            notes = notes.filter(subject_id=self.subject_id)

        return notes

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subjects'] = self.request.user.subjects.all()  # for the filter dropdown
        context['query'] = self.query
        context['selected_subject'] = self.subject_id
        context['is_filtered'] = bool(self.query or self.subject_id)
        return context


class NoteDetailView(OwnerMixin, DetailView):
    model = Note

    def get_queryset(self):
        return super().get_queryset().select_related('subject')


class NoteCreateView(LoginRequiredMixin, UserFormMixin, SuccessMessageMixin, CreateView):
    model = Note
    form_class = NoteForm
    success_message = 'Note "%(title)s" was created.'

    def get(self, request, *args, **kwargs):
        # A note needs a subject, so send new users to create one first
        if not request.user.subjects.exists():
            messages.info(request, 'Create a subject first, then you can add notes to it.')
            return redirect('subject_create')
        return super().get(request, *args, **kwargs)

    def get_initial(self):
        # /notes/new/?subject=3 pre-selects that subject in the dropdown
        return {'subject': self.request.GET.get('subject')}


class NoteUpdateView(OwnerMixin, UserFormMixin, SuccessMessageMixin, UpdateView):
    model = Note
    form_class = NoteForm
    success_message = 'Note "%(title)s" was updated.'


class NoteDeleteView(OwnerMixin, DeleteMessageMixin, DeleteView):
    model = Note
    success_url = reverse_lazy('note_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.file:
            context['warning'] = 'The attached PDF will be deleted too.'
        return context


# sameorigin lets our own note page show the PDF in an <iframe>
@method_decorator(xframe_options_sameorigin, name='dispatch')
class NoteFileView(OwnerMixin, SingleObjectMixin, View):
    """Sends a note's PDF only to its owner.

    PDFs are served through this view instead of a public /media/ URL,
    so nobody can open another user's file by guessing its address.
    """

    model = Note

    def get(self, request, *args, **kwargs):
        note = self.get_object()  # 404 if it isn't the user's note
        if not note.file:
            raise Http404('This note has no PDF.')
        try:
            file = note.file.open('rb')
        except FileNotFoundError:
            raise Http404('The PDF file is missing.')
        return FileResponse(file, content_type='application/pdf',
                            filename=os.path.basename(note.file.name))
