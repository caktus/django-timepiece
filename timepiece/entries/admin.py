from django.contrib import admin

from timepiece.entries.models import Activity, ActivityGroup, Entry, Location,\
        ProjectHours


class ActivityAdmin(admin.ModelAdmin):
    model = Activity
    list_display = ('code', 'name', 'billable')
    list_filter = ('billable',)


class ActivityGroupAdmin(admin.ModelAdmin):
    model = ActivityGroup
    list_display = ('name',)
    list_filter = ('activities',)
    filter_horizontal = ('activities',)


class EntryAdmin(admin.ModelAdmin):
    model = Entry
    list_display = ('user',
                    'project',
                    'location',
                    'project_type',
                    'activity',
                    'start_time',
                    'end_time',
                    'hours',
                    'is_closed',
                    'is_paused',
                    )
    list_filter = ['activity', 'project__type', 'user', 'project']
    search_fields = ['user__first_name', 'user__last_name', 'project__name',
                     'activity__name', 'comments']
    date_hierarchy = 'start_time'
    ordering = ('-start_time',)

    def project_type(self, entry):
        return entry.project.type


class LocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


class ProjectHoursAdmin(admin.ModelAdmin):
    list_display = ('_user', 'project', 'week_start', 'hours', 'published')

    def _user(self, obj):
        return obj.user.get_name_or_username()
    _user.short_description = 'User'
    _user.admin_order_field = 'user__last_name'


admin.site.register(Activity, ActivityAdmin)
admin.site.register(ActivityGroup, ActivityGroupAdmin)
admin.site.register(Entry, EntryAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(ProjectHours, ProjectHoursAdmin)
