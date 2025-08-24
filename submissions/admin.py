from django.contrib import admin
from .models import Submission

class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'problem', 'language', 'verdict', 'execution_time', 'submitted_at')
    list_filter = ('verdict', 'language', 'submitted_at')
    search_fields = ('user__username', 'problem__title')
    readonly_fields = ('submitted_at',)

admin.site.register(Submission, SubmissionAdmin)