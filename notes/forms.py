from django import forms

from accounts.forms import BootstrapFormMixin

from .models import Note, Subject


class SubjectForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'description']  # "user" is set from the logged-in user, not the form
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.instance.user = user

    def clean_name(self):
        # "user" isn't a form field, so Django won't check the unique
        # (user, name) rule for us. Check it here to show a friendly error.
        name = self.cleaned_data['name'].strip()
        duplicates = Subject.objects.filter(user=self.user, name__iexact=name).exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError('You already have a subject with this name.')
        return name


class NoteForm(BootstrapFormMixin, forms.ModelForm):
    # Extra checkbox (not a model field) shown when editing a note that has a PDF
    remove_file = forms.BooleanField(required=False, label='Remove the current PDF')

    class Meta:
        model = Note
        fields = ['subject', 'title', 'content', 'file']
        labels = {'file': 'PDF file'}
        help_texts = {'file': 'Optional. PDF files only, up to 10 MB.'}
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
            # accept= makes the browser's file picker show PDFs only
            'file': forms.FileInput(attrs={'accept': 'application/pdf'}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.user = user
        # Only offer the user's own subjects in the dropdown.
        # Posting another user's subject id fails with "Select a valid choice".
        self.fields['subject'].queryset = user.subjects.all()
        if not self.instance.file:
            del self.fields['remove_file']  # nothing to remove yet

    def save(self, commit=True):
        # Clear the file if asked, unless a new one was uploaded at the same time
        if self.cleaned_data.get('remove_file') and 'file' not in self.changed_data:
            self.instance.file = None
        return super().save(commit)
