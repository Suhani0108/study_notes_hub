from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from .validators import validate_pdf


class Subject(models.Model):
    """A topic a user studies, e.g. 'Biology' or 'Django'."""

    # Each subject belongs to one user. Deleting the user deletes their subjects.
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # set once, on creation

    class Meta:
        ordering = ['name']
        # One user can't have two subjects with the same name
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_subject_per_user'),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        # Create/Update views redirect here after saving
        return reverse('subject_detail', args=[self.pk])


class Note(models.Model):
    """A single note inside a subject. Can hold text, a PDF, or both."""

    # Each note lives in one subject. Deleting the subject deletes its notes.
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='notes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)  # optional text
    file = models.FileField(
        upload_to='notes/pdfs/%Y/%m/',  # saved under media/notes/pdfs/<year>/<month>/
        blank=True,                     # optional
        validators=[validate_pdf],
    )
    created_at = models.DateTimeField(auto_now_add=True)  # set once, on creation
    updated_at = models.DateTimeField(auto_now=True)      # updated on every save

    class Meta:
        ordering = ['-updated_at']  # most recently edited first

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('note_detail', args=[self.pk])

    def clean(self):
        # Stop a note from being filed under someone else's subject
        if self.subject_id and self.user_id and self.subject.user_id != self.user_id:
            raise ValidationError({'subject': 'You can only add notes to your own subjects.'})
