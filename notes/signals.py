"""Keep the media/ folder tidy: delete PDF files nobody uses any more.

Django deletes database rows, but never the uploaded files on disk.
These signal handlers run automatically when a Note is saved or deleted.
"""
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import Note


@receiver(post_delete, sender=Note)
def delete_file_with_note(sender, instance, **kwargs):
    # Also runs when a note is deleted because its subject or user was deleted
    if instance.file:
        instance.file.delete(save=False)


@receiver(pre_save, sender=Note)
def delete_old_file_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return  # brand-new note, no old file to clean up
    old_name = Note.objects.filter(pk=instance.pk).values_list('file', flat=True).first()
    # The file was replaced or removed, so delete the old one
    if old_name and old_name != instance.file.name:
        instance.file.storage.delete(old_name)
