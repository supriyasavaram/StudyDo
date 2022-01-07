from django.contrib import admin
from .models import Upload
# Register your models here.

class UploadAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['title', 'classes']})

    ]
admin.site.register(Upload, UploadAdmin)