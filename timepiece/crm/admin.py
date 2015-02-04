from django.contrib import admin

from timepiece.crm.models import (
    Attribute, Business, Project, RelationshipType, UserProfile)


class AttributeAdmin(admin.ModelAdmin):
    search_fields = ('label', 'type')
    list_display = ('label', 'type', 'enable_timetracking', 'billable')
    list_filter = ('type', 'enable_timetracking', 'billable')
    ordering = ('type', 'sort_order')  # Django honors only first field.


class BusinessAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name']
    search_fields = ['name', 'short_name']


class ProjectAdmin(admin.ModelAdmin):
    raw_id_fields = ('business',)
    list_display = ('name', 'business', 'point_person', 'status', 'type')
    list_filter = ('type', 'status')
    search_fields = ('name', 'business__name', 'point_person__username',
                     'point_person__first_name', 'point_person__last_name',
                     'description')


class RelationshipTypeAdmin(admin.ModelAdmin):
    pass


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'hours_per_week')


admin.site.register(Attribute, AttributeAdmin)
admin.site.register(Business, BusinessAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(RelationshipType, RelationshipTypeAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
