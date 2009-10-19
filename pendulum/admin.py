from django.contrib import admin
from pendulum import models as pendulum

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
    model = pendulum.Activity
    list_display = ('code', 'name', 'log_count', 'total_hours')

class EntryAdmin(admin.ModelAdmin):
    model = pendulum.Entry
    list_display = ('user',
                    'project',
                    'activity',
                    'start_time',
                    'end_time',
                    'hours',
                    'is_closed',
                    'is_paused')
    list_filter = ['project']
    search_fields = ['user', 'project', 'activity', 'comments']
    date_hierarchy = 'start_time'

class ProjectAdmin(admin.ModelAdmin):
    model = pendulum.Project
    list_display = ('name', 'is_active', 'log_count', 'total_hours')


class RepeatPeriodAdmin(admin.ModelAdmin):
    list_display = ('project', 'count', 'interval')
    list_filter = ('interval',)
admin.site.register(pendulum.RepeatPeriod, RepeatPeriodAdmin)


class BillingWindowAdmin(admin.ModelAdmin):
    list_display = ('id', 'period', 'date', 'end_date')
    list_filter = ('period',)
admin.site.register(pendulum.BillingWindow, BillingWindowAdmin)


admin.site.register(pendulum.PendulumConfiguration, PendulumConfigurationAdmin)
admin.site.register(pendulum.Activity, ActivityAdmin)
admin.site.register(pendulum.Entry, EntryAdmin)
admin.site.register(pendulum.Project, ProjectAdmin)
