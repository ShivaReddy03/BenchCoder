from django.contrib import admin
from .models import Problem, TestCase

class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 1

class ProblemAdmin(admin.ModelAdmin):
    list_display = ('title', 'difficulty', 'points', 'created_at')
    list_filter = ('difficulty', 'created_at')
    search_fields = ('title', 'description')
    inlines = [TestCaseInline]

admin.site.register(Problem, ProblemAdmin)
admin.site.register(TestCase)