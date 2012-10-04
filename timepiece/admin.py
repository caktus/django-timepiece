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
admin.site.register(timepiece.HourGroup, HourGroupAdmin)


class ActivityGroupAdmin(admin.ModelAdmin):
    model = timepiece.ActivityGroup
    list_display = ('name',)
    list_filter = ('activities',)
admin.site.register(timepiece.ActivityGroup, ActivityGroupAdmin)


class RelationshipTypeAdmin(admin.ModelAdmin):
    pass
admin.site.register(timepiece.RelationshipType, RelationshipTypeAdmin)


class BusinessAdmin(admin.ModelAdmin):
    pass
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


class ContractMilestoneInline(admin.TabularInline):
    model = timepiece.ContractMilestone


class ProjectContractAdmin(admin.ModelAdmin):
    model = timepiece.ProjectContract
    list_display = ('_project', 'start_date', 'end_date', 'status',
                    'num_hours', 'hours_assigned', 'hours_unassigned',
                    'hours_worked')
    ordering = ('-end_date',)
    inlines = (ContractAssignmentInline, ContractMilestoneInline)
    list_filter = ('status',)
    raw_id_fields = ('project',)
    list_per_page = 20

    def _project(self, obj):
        return obj.project.name
    _project.admin_order_field = 'project__name'
    _project.short_description = 'Project'

    def hours_unassigned(self, obj):
        return obj.num_hours - obj.hours_assigned

admin.site.register(timepiece.ProjectContract, ProjectContractAdmin)


class ProjectContractInline(admin.TabularInline):
    model = timepiece.ProjectContract
    extra = 0


class ProjectAdmin(admin.ModelAdmin):
    model = timepiece.Project
    raw_id_fields = ('business',)
    list_display = ('name', 'business', 'point_person', 'status', 'type',)
    list_filter = ('type', 'status')
    inlines = (ProjectContractInline,)
admin.site.register(timepiece.Project, ProjectAdmin)


class ContractAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'contract', 'user', 'start_date',
                    'end_date', 'min_hours_per_week', 'num_hours', 'worked',
                    'remaining')
    list_filter = ('contract',)
    ordering = ('-start_date',)

    def queryset(self, request):
        qs = super(ContractAssignmentAdmin, self).queryset(request)
        return qs.exclude(contract__status='complete')

    def worked(self, obj):
        hours_worked = float(obj.hours_worked)
        if obj.num_hours:
            percent = hours_worked * 100.0 / float(obj.num_hours)
            return "%.2f (%.2f%%)" % (hours_worked, percent)
        return ""

    def remaining(self, obj):
        return "%.2f" % (obj.hours_remaining,)

admin.site.register(timepiece.ContractAssignment, ContractAssignmentAdmin)


class LocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
admin.site.register(timepiece.Location, LocationAdmin)


class ProjectHoursAdmin(admin.ModelAdmin):
    list_display = ('_person', 'project', 'week_start', 'hours', 'published')

    def _person(self, obj):
        return obj.user.get_full_name()
    _person.short_description = 'Person'
    _person.admin_order_field = 'user__last_name'

admin.site.register(timepiece.ProjectHours, ProjectHoursAdmin)


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'hours_per_week')
admin.site.register(timepiece.UserProfile, UserProfileAdmin)
