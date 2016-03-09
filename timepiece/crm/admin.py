from django.contrib import admin

from timepiece.crm.models import (Attribute, Business, Project,
        RelationshipType, UserProfile, PaidTimeOffRequest,
        PaidTimeOffLog, Milestone, ActivityGoal,
        Contact, ContactNote, BusinessNote, BusinessAttachment,
        Lead, LeadNote, LeadAttachment, DistinguishingValueChallenge, 
        TemplateDifferentiatingValue, DVCostItem,
        MilestoneNote)


class AttributeAdmin(admin.ModelAdmin):
    search_fields = ('label', 'type')
    list_display = ('label', 'type', 'enable_timetracking', 'billable')
    list_filter = ('type', 'enable_timetracking', 'billable')
    ordering = ('type', 'sort_order')  # Django honors only first field.


class BusinessAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name']
    search_fields = ['name', 'short_name']

class BusinessNoteAdmin(admin.ModelAdmin):
    pass

class BusinessAttachmentAdmin(admin.ModelAdmin):
    pass

class ProjectAdmin(admin.ModelAdmin):
    raw_id_fields = ('business',)
    list_display = ('name', 'business', 'point_person', 'status', 'type')
    list_filter = ('type', 'status')
    search_fields = ('name', 'business__name', 'point_person__username',
                     'point_person__first_name', 'point_person__last_name',
                     'description')

class ContactAdmin(admin.ModelAdmin):
    pass

class ContactNoteAdmin(admin.ModelAdmin):
    pass

class LeadAdmin(admin.ModelAdmin):
    pass

class LeadNoteAdmin(admin.ModelAdmin):
    pass

class LeadAttachmentAdmin(admin.ModelAdmin):
    pass

class RelationshipTypeAdmin(admin.ModelAdmin):
    pass

class PTORequestAdmin(admin.ModelAdmin):
    pass

class PTOLogAdmin(admin.ModelAdmin):
    pass

class MilestoneAdmin(admin.ModelAdmin):
    pass

class ActivityGoalAdmin(admin.ModelAdmin):
    pass


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'hours_per_week')


admin.site.register(Attribute, AttributeAdmin)
admin.site.register(Business, BusinessAdmin)
admin.site.register(BusinessNote, BusinessNoteAdmin)
admin.site.register(BusinessAttachment, BusinessAttachmentAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(RelationshipType, RelationshipTypeAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(PaidTimeOffRequest, PTORequestAdmin)
admin.site.register(PaidTimeOffLog, PTOLogAdmin)
admin.site.register(Milestone, MilestoneAdmin)
admin.site.register(MilestoneNote)
admin.site.register(ActivityGoal, ActivityGoalAdmin)
admin.site.register(Contact, ContactAdmin)
admin.site.register(ContactNote, ContactNoteAdmin)
admin.site.register(Lead, LeadAdmin)
admin.site.register(LeadNote, LeadNoteAdmin)
admin.site.register(LeadAttachment, LeadAttachmentAdmin)
admin.site.register(DistinguishingValueChallenge)
admin.site.register(TemplateDifferentiatingValue)
admin.site.register(DVCostItem)
