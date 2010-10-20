from django.contrib import admin
from timepiece import models as timepiece

class ActivityAdmin(admin.ModelAdmin):
    model = timepiece.Activity
    list_display = ('code', 'name')
admin.site.register(timepiece.Activity, ActivityAdmin)


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
    search_fields = ['user', 'project', 'activity', 'comments']
    date_hierarchy = 'start_time'
admin.site.register(timepiece.Entry, EntryAdmin)


class AttributeAdmin(admin.ModelAdmin):
    search_fields = ('label', 'type')
    list_display = ('label', 'type')
    list_filter = ('type',)
    ordering = ('type', 'sort_order',) # Django honors only first field
admin.site.register(timepiece.Attribute, AttributeAdmin)


class ContractAssignmentInline(admin.TabularInline):
    model = timepiece.ContractAssignment


class ProjectContractAdmin(admin.ModelAdmin):
    model = timepiece.ProjectContract
    list_display = ('project', 'start_date', 'end_date', 'num_hours',
                    'hours_assigned', 'hours_worked')
    ordering = ('end_date',)
    inlines = (ContractAssignmentInline,)
admin.site.register(timepiece.ProjectContract, ProjectContractAdmin)


class ProjectContractInline(admin.TabularInline):
    model = timepiece.ProjectContract


class ProjectAdmin(admin.ModelAdmin):
    model = timepiece.Project
    raw_id_fields = ('interactions', 'business')
    list_display = ('name', 'business', 'point_person', 'status', 'type',)
    list_filter = ('type', 'status')
    inlines = (ProjectContractInline,)
admin.site.register(timepiece.Project, ProjectAdmin)


class ContractAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'contract', 'contact', 'start_date',
                    'end_date', 'num_hours', 'worked', 'remaining')
    list_filter = ('contract', 'contact')
    ordering = ('-start_date',)
    
    def worked(self, obj):
        hours_worked = float(obj.hours_worked)
        percent = hours_worked * 100.0 / obj.num_hours
        return "%.2f (%.2f%%)" % (hours_worked, percent)

    def remaining(self, obj):
        return "%.2f" % (obj.hours_remaining,)
admin.site.register(timepiece.ContractAssignment, ContractAssignmentAdmin)


class PersonScheduleAdmin(admin.ModelAdmin):
    list_display = ('contact', 'hours_per_week', 'end_date', 'total_available',
                    'scheduled', 'unscheduled')

    def total_available(self, obj):
        return "%.2f" % (obj.hours_available,)
  
    def scheduled(self, obj):
        return "%.2f" % (obj.hours_scheduled,)
  
    def unscheduled(self, obj):
        return "%.2f" % (obj.hours_available - float(obj.hours_scheduled),)
admin.site.register(timepiece.PersonSchedule, PersonScheduleAdmin)


class RepeatPeriodAdmin(admin.ModelAdmin):
    list_display = ('count', 'interval')
    list_filter = ('interval',)
admin.site.register(timepiece.RepeatPeriod, RepeatPeriodAdmin)


class BillingWindowAdmin(admin.ModelAdmin):
    list_display = ('id', 'period', 'date', 'end_date')
    list_filter = ('period',)
admin.site.register(timepiece.BillingWindow, BillingWindowAdmin)

class LocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
admin.site.register(timepiece.Location, LocationAdmin)

