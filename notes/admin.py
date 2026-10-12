from django.contrib import admin

from .models import Note, Subject


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')          # columns in the list page
    list_filter = ('user', 'created_at')                   # sidebar filters
    search_fields = ('name', 'description')                # search box
    date_hierarchy = 'created_at'                          # date drill-down bar


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'user', 'has_file', 'created_at', 'updated_at')
    list_filter = ('subject', 'user', 'created_at', 'updated_at')
    search_fields = ('title', 'content', 'subject__name')  # "__" searches a related field
    readonly_fields = ('created_at', 'updated_at')         # shown but not editable
    date_hierarchy = 'created_at'

    @admin.display(boolean=True, description='PDF')
    def has_file(self, obj):
        # Shows a green tick / red cross in the list
        return bool(obj.file)
