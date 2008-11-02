from django.contrib import admin
from pendulum.models import PendulumConfiguration, Activity, Entry, Project

class PendulumConfigurationAdmin(admin.ModelAdmin):
    list_display = ('site',
                    'current_mode',
                    'is_monthly',
                    'month_start',
                    'install_date',
                    'period_length')
    list_filter = ['is_monthly']
    search_fields = ['site']
    fieldsets = (
        (None, {
            'fields': ('site',)
        }),
        ('Month-Long Periods', {
            'fields': ('is_monthly', 'month_start'),
        }),
        ('Fixed-Length Periods', {
            'fields': ('install_date', 'period_length'),
        })
    )

class ActivityAdmin(admin.ModelAdmin):
    model = Activity
    list_display = ('code', 'name', 'log_count', 'total_hours')

class EntryAdmin(admin.ModelAdmin):
    model = Entry
    list_display = ('user', 'project', 'activity', 'start_time', 'end_time', 'hours')
    list_filter = ['project']
    search_fields = ['user', 'project', 'activity', 'comments']
    date_hierarchy = 'start_time'

class ProjectAdmin(admin.ModelAdmin):
    model = Project
    list_display = ('name', 'is_active', 'log_count', 'total_hours')

admin.site.register(PendulumConfiguration, PendulumConfigurationAdmin)
admin.site.register(Activity, ActivityAdmin)
admin.site.register(Entry, EntryAdmin)
admin.site.register(Project, ProjectAdmin)
