from django.apps import AppConfig


class NotesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notes'

    def ready(self):
        # Importing the module connects the signal handlers
        from . import signals  # noqa: F401
