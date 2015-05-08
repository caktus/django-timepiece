from django.contrib import admin

from timepiece.contracts.models import (
    ProjectContract, ContractHour, ContractAssignment, HourGroup)


class ContractAssignmentInline(admin.TabularInline):
    model = ContractAssignment
    raw_id_fields = ('user',)

    def get_queryset(self, request):
        qs = super(ContractAssignmentInline, self).get_queryset(request)
        return qs.select_related()


class ContractHourInline(admin.TabularInline):
    model = ContractHour


class ProjectContractAdmin(admin.ModelAdmin):
    model = ProjectContract
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


class HourGroupAdmin(admin.ModelAdmin):
    model = HourGroup
    list_display = ('name',)
    list_filter = ('activities',)
    ordering = ('order', 'name')
    filter_horizontal = ('activities',)


admin.site.register(ProjectContract, ProjectContractAdmin)
admin.site.register(HourGroup, HourGroupAdmin)
admin.site.register(ContractHour)
