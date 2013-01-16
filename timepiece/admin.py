from django.contrib import admin
from timepiece import models as timepiece


class ActivityAdmin(admin.ModelAdmin):
    model = timepiece.Activity
    list_display = ('code', 'name', 'billable')
    list_filter = ('billable',)
admin.site.register(timepiece.Activity, ActivityAdmin)


class HourGroupAdmin(admin.ModelAdmin):
    model = timepiece.HourGroup
    list_display = ('name',)
    list_filter = ('activities',)
    ordering = ('order', 'name')
    filter_horizontal = ('activities',)
admin.site.register(timepiece.HourGroup, HourGroupAdmin)


class ActivityGroupAdmin(admin.ModelAdmin):
    model = timepiece.ActivityGroup
    list_display = ('name',)
    list_filter = ('activities',)
    filter_horizontal = ('activities',)
admin.site.register(timepiece.ActivityGroup, ActivityGroupAdmin)


class RelationshipTypeAdmin(admin.ModelAdmin):
    pass
admin.site.register(timepiece.RelationshipType, RelationshipTypeAdmin)


class BusinessAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name']
    search_fields = ['name', 'short_name']
admin.site.register(timepiece.Business, BusinessAdmin)


class EntryAdmin(admin.ModelAdmin):
    model = timepiece.Entry
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
admin.site.register(timepiece.Entry, EntryAdmin)


class AttributeAdmin(admin.ModelAdmin):
    search_fields = ('label', 'type')
    list_display = ('label', 'type', 'enable_timetracking', 'billable')
    list_filter = ('type', 'enable_timetracking', 'billable')
    #Django honors only first field
    ordering = ('type', 'sort_order')
admin.site.register(timepiece.Attribute, AttributeAdmin)


class ContractAssignmentInline(admin.TabularInline):
    model = timepiece.ContractAssignment
    raw_id_fields = ('user',)

    def queryset(self, request):
        qs = super(ContractAssignmentInline, self).queryset(request)
        return qs.select_related()


class ContractHourInline(admin.TabularInline):
    model = timepiece.ContractHour

class ProjectContractAdmin(admin.ModelAdmin):
    model = timepiece.ProjectContract
    list_display = ('name', 'start_date', 'end_date', 'status',
                    'contracted_hours', 'pending_hours',
                    'hours_assigned', 'hours_unassigned',
                    'hours_worked',
                    'type')
    inlines = (ContractAssignmentInline, ContractHourInline)
    list_filter = ('status', 'type')
    filter_horizontal = ('projects',)
    list_per_page = 20
    search_fields = ('name', 'projects__name', 'projects__business__name')

    def hours_unassigned(self, obj):
        return obj.contracted_hours() - obj.hours_assigned

admin.site.register(timepiece.ProjectContract, ProjectContractAdmin)


class ProjectAdmin(admin.ModelAdmin):
    raw_id_fields = ('business',)
    list_display = ('name', 'business', 'point_person', 'status', 'type')
    list_filter = ('type', 'status')
    search_fields = ('name', 'business__name', 'point_person__username',
            'point_person__first_name', 'point_person__last_name',
            'description')
admin.site.register(timepiece.Project, ProjectAdmin)


class LocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
admin.site.register(timepiece.Location, LocationAdmin)


class ProjectHoursAdmin(admin.ModelAdmin):
    list_display = ('_user', 'project', 'week_start', 'hours', 'published')

    def _user(self, obj):
        return obj.user.get_full_name()
    _user.short_description = 'User'
    _user.admin_order_field = 'user__last_name'

admin.site.register(timepiece.ProjectHours, ProjectHoursAdmin)


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'hours_per_week')
admin.site.register(timepiece.UserProfile, UserProfileAdmin)
