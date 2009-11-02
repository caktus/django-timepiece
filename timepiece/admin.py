from django.contrib import admin
from timepiece import models as timepiece

class ActivityAdmin(admin.ModelAdmin):
    model = timepiece.Activity
    list_display = ('code', 'name')

class EntryAdmin(admin.ModelAdmin):
    model = timepiece.Entry
    list_display = ('user',
                    'project',
                    'location',
                    'activity',
                    'start_time',
                    'end_time',
                    'hours',
                    'is_closed',
                    'is_paused')
    list_filter = ['user', 'project']
    list_editable = ['location']
    search_fields = ['user', 'project', 'activity', 'comments']
    date_hierarchy = 'start_time'

class ProjectAdmin(admin.ModelAdmin):
    model = timepiece.Project
    raw_id_fields = ('interactions', 'business')
    list_display = ('name', 'business', 'point_person', 'status', 'type',)
    list_filter = ('type', 'status')


class RepeatPeriodAdmin(admin.ModelAdmin):
    list_display = ('count', 'interval')
    list_filter = ('interval',)
admin.site.register(timepiece.RepeatPeriod, RepeatPeriodAdmin)


class BillingWindowAdmin(admin.ModelAdmin):
    list_display = ('id', 'period', 'date', 'end_date')
    list_filter = ('period',)
admin.site.register(timepiece.BillingWindow, BillingWindowAdmin)


admin.site.register(timepiece.Activity, ActivityAdmin)
admin.site.register(timepiece.Entry, EntryAdmin)
admin.site.register(timepiece.Project, ProjectAdmin)
