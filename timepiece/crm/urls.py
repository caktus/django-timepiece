from django.conf.urls import patterns, url

from timepiece.crm import views


urlpatterns = patterns('',
    # Search
    url(r'^quick_search/$',
        views.QuickSearch.as_view(),
        name='quick_search'),

    # Users
    url(r'^user/settings/$',
        views.EditSettings.as_view(),
        name='edit_settings'),
    url(r'^user/$',
        views.ListUsers.as_view(),
        name='list_users'),
    url(r'^user/create/$',
        views.CreateUser.as_view(),
        name='create_user'),
    url(r'^user/(?P<user_id>\d+)/$',
        views.ViewUser.as_view(),
        name='view_user'),
    url(r'^user/(?P<user_id>\d+)/edit/$',
        views.EditUser.as_view(),
        name='edit_user'),
    url(r'^user/(?P<user_id>\d+)/limited-profile/create/$',
        views.CreateLimitedAccessUserProfile.as_view(),
        name='create_limited_profile'),
    url(r'^user/(?P<user_id>\d+)/limited-profile/(?P<profile_id>\d+)/edit/$',
        views.EditLimitedAccessUserProfile.as_view(),
        name='edit_limited_profile'),
    url(r'^user/(?P<user_id>\d+)/delete/$',
        views.DeleteUser.as_view(),
        name='delete_user'),

    # User timesheets
    url(r'^user/(?P<user_id>\d+)/timesheet/' +
                '(?:(?P<active_tab>overview|all-entries|daily-summary)/)?$',
        views.view_user_timesheet,
        name='view_user_timesheet'),
    url(r'^user/(?P<user_id>\d+)/timesheet/reject/$',
        views.reject_user_timesheet,
        name='reject_user_timesheet'),
    url(r'^user/(?P<user_id>\d+)/timesheet/(?P<action>verify|approve)/$',
        views.change_user_timesheet,
        name='change_user_timesheet'),

    # Projects
    url(r'^project/$',
        views.ListProjects.as_view(),
        name='list_projects'),
    url(r'^project/create/$',
        views.CreateProject.as_view(),
        name='create_project'),
    url(r'^project/(?P<project_id>\d+)/$',
        views.ViewProject.as_view(),
        name='view_project'),
    url(r'^project/(?P<project_id>\d+)/edit/$',
        views.EditProject.as_view(),
        name='edit_project'),
    url(r'^project/(?P<project_id>\d+)/delete/$',
        views.DeleteProject.as_view(),
        name='delete_project'),
    url(r'^project/(?P<project_id>\d+)/activities/$',
        views.get_project_activities,
        name='project_activities'),
    # Get Tags / Add Tag
    url(r'^project/(?P<project_id>\d+)/tags/$',
        views.ProjectTags.as_view(),
        name='project_tags'),
    # Remove Tag
    url(r'^project/(?P<project_id>\d+)/tags/remove$',
        views.RemoveProjectTag.as_view(),
        name='remove_project_tag'),
    # Project Atachments
    url(r'^project/(?P<project_id>\d+)/attachment/s3/$',
        views.project_s3_attachment,
        name='s3_project_attachment'),
    url(r'^project/(?P<project_id>\d+)/attachment/(?P<attachment_id>\d+)/$',
        views.project_download_attachment,
        name='download_project_attachment'),

    # Project timesheets
    url(r'^project/(?P<project_id>\d+)/timesheet/$',
        views.ProjectTimesheet.as_view(),
        name='view_project_timesheet'),

    # Project General Tasks
    # Add General Task
    url(r'^project/(?P<project_id>\d+)/add-general-task$',
        views.AddProjectGeneralTask.as_view(),
        name='project_add_general_task'),
    # Remove General Task
    url(r'^project/(?P<project_id>\d+)/remove-general-task$',
        views.RemoveProjectGeneralTask.as_view(),
        name='project_remove_general_task'),

    # Businesses
    url(r'^business/$',
        views.ListBusinesses.as_view(),
        name='list_businesses'),
    url(r'^business/json$',
        views.business,
        name='get_business_list'),
    url(r'^business/create/$',
        views.CreateBusiness.as_view(),
        name='create_business'),
    url(r'^business/(?P<business_id>\d+)/$',
        views.ViewBusiness.as_view(),
        name='view_business'),
    url(r'^business/(?P<business_id>\d+)/edit/$',
        views.EditBusiness.as_view(),
        name='edit_business'),
    url(r'^business/(?P<business_id>\d+)/delete/$',
        views.DeleteBusiness.as_view(),
        name='delete_business'),
    url(r'^business/(?P<business_id>\d+)/get_users/$',
        views.get_users_for_business,
        name='get_users_for_business'),
    url(r'^business/(?P<business_id>\d+)/department/create/$',
        views.CreateBusinessDepartment.as_view(),
        name='create_business_department'),
    url(r'^business/(?P<business_id>\d+)/department/(?P<business_department_id>\d+)/edit/$',
        views.EditBusinessDepartment.as_view(),
        name='edit_business_department'),
    url(r'^business/(?P<business_id>\d+)/department/(?P<business_department_id>\d+)/$',
        views.ViewBusinessDepartment.as_view(),
        name='view_business_department'),
    url(r'^business/(?P<business_id>\d+)/department/(?P<business_department_id>\d+)/delete/$',
        views.DeleteBusinessDepartment.as_view(),
        name='delete_business_department'),

    # Add Business Note
    url(r'^business/(?P<business_id>\d+)/add_note$', # expects querystring of transition_id=<int>
        views.AddBusinessNote.as_view(),
        name='add_business_note'),
    
    # Business Attachments
    url(r'^business/(?P<business_id>\d+)/add-attachment$', # expects querystring of transition_id=<int>
        views.business_upload_attachment,
        name='add_business_attachment'),
    url(r'^business/(?P<business_id>\d+)/download-attachment/(?P<attachment_id>\w+)/$',
        views.business_download_attachment,
        name='download_business_attachment'),

    # Business Tags

    # Get Tags / Add Tag
    url(r'^business/(?P<business_id>\d+)/tags/$',
        views.BusinessTags.as_view(),
        name='business_tags'),
    # Remove Tag
    url(r'^business/(?P<business_id>\d+)/tags/remove$',
        views.RemoveBusinessTag.as_view(),
        name='remove_business_tag'),

    # User-project relationships
    url(r'^relationship/create/$',
        views.CreateRelationship.as_view(),
        name='create_relationship'),
    url(r'^relationship/edit/$',
        views.EditRelationship.as_view(),
        name='edit_relationship'),
    url(r'^relationship/delete/$',
        views.DeleteRelationship.as_view(),
        name='delete_relationship'),
    

    # Paid Time Off
    url(r'^pto/(?:(?P<active_tab>summary|requests|history|current_pto|approvals|all_history|all_request_history)/)?$',
        views.pto_home,
        name='pto'),
    url(r'^pto/request/(?P<pto_request_id>\d+)$',
        views.pto_request_details,
        name='pto_request_details'),
    url(r'^pto/request/create/$',
        views.CreatePTORequest.as_view(),
        name='create_pto_request'),
    url(r'^pto/request/(?P<pto_request_id>\d+)/edit/$',
        views.EditPTORequest.as_view(),
        name='edit_pto_request'),
    url(r'^pto/request/(?P<pto_request_id>\d+)/delete/$',
        views.DeletePTORequest.as_view(),
        name='delete_pto_request'),
    url(r'^pto/request/(?P<pto_request_id>\d+)/approve/$',
        views.ApprovePTORequest.as_view(),
        name='approve_pto_request'),
    url(r'^pto/request/(?P<pto_request_id>\d+)/process/$',
        views.ProcessPTORequest.as_view(),
        name='process_pto_request'),
    url(r'^pto/request/(?P<pto_request_id>\d+)/deny/$',
        views.DenyPTORequest.as_view(),
        name='deny_pto_request'),
    url(r'^pto/log/create/$',
        views.CreatePTOLogEntry.as_view(),
        name='create_pto_log'),
    url(r'^pto/log/(?P<pto_log_id>\d+)/edit/$',
        views.EditPTOLogEntry.as_view(),
        name='edit_pto_log'),
    url(r'^pto/log/(?P<pto_log_id>\d+)/delete/$',
        views.DeletePTOLogEntry.as_view(),
        name='delete_pto_log'),

    
    # Milestones
    url(r'^project/(?P<project_id>\d+)/milestone/(?P<milestone_id>\d+)/$',
        views.ViewMilestone.as_view(),
        name='view_milestone'),
    url(r'^project/(?P<project_id>\d+)/milestone/create/$',
        views.CreateMilestone.as_view(),
        name='create_milestone'),
    url(r'^project/(?P<project_id>\d+)/milestone/(?P<milestone_id>\d+)/edit/$',
        views.EditMilestone.as_view(),
        name='edit_milestone'),
    url(r'^project/(?P<project_id>\d+)/milestone/(?P<milestone_id>\d+)/delete/$',
        views.DeleteMilestone.as_view(),
        name='delete_milestone'),

    
    # Activity Goals
    url(r'^project/(?P<project_id>\d+)/activity_goal/create/$',
        views.CreateActivityGoal.as_view(),
        name='create_activity_goal'),
    url(r'^project/(?P<project_id>\d+)/activity_goal/(?P<activity_goal_id>\d+)/edit/$',
        views.EditActivityGoal.as_view(),
        name='edit_activity_goal'),
    url(r'^project/(?P<project_id>\d+)/activity_goal/(?P<activity_goal_id>\d+)/delete/$',
        views.DeleteActivityGoal.as_view(),
        name='delete_activity_goal'),

    # Burnup Charts
    url(r'^project/(?P<project_id>\d+)/burnup_chart_data/$',
        views.burnup_chart_data,
        name='project_burnup_chart_data'),
    url(r'^project/(?P<project_id>\d+)/burnup_chart/$',
        views.burnup_chart,
        name='project_burnup_chart'),



    # Contacts
    url(r'^contact/$',
        views.ListContacts.as_view(),
        name='list_contacts'),
    url(r'^contact/create/$',
        views.CreateContact.as_view(),
        name='create_contact'),
    url(r'^contact/(?P<contact_id>\d+)/$',
        views.ViewContact.as_view(),
        name='view_contact'),
    url(r'^contact/(?P<contact_id>\d+)/edit/$',
        views.EditContact.as_view(),
        name='edit_contact'),
    url(r'^contact/(?P<contact_id>\d+)/delete/$',
        views.DeleteContact.as_view(),
        name='delete_contact'),
    # Add Contact Note
    url(r'^contact/(?P<contact_id>\d+)/add_note$',
        views.AddContactNote.as_view(),
        name='add_contact_note'),
    # Get Tags / Add Tag
    url(r'^contact/(?P<contact_id>\d+)/tags/$',
        views.ContactTags.as_view(),
        name='contact_tags'),
    # Remove Tag
    url(r'^contact/(?P<contact_id>\d+)/tags/remove$',
        views.RemoveContactTag.as_view(),
        name='remove_contact_tag'),


    # Leads
    url(r'^lead/$',
        views.ListLeads.as_view(),
        name='list_leads'),
    url(r'^lead/create/$',
        views.CreateLead.as_view(),
        name='create_lead'),
    url(r'^lead/(?P<lead_id>\d+)/edit/$',
        views.EditLead.as_view(),
        name='edit_lead'),
    url(r'^lead/(?P<lead_id>\d+)/delete/$',
        views.DeleteLead.as_view(),
        name='delete_lead'),

    url(r'^lead/(?P<lead_id>\d+)/$',
        views.ViewLeadGeneralInfo.as_view(),
        name='view_lead'),
    url(r'^lead/(?P<lead_id>\d+)/differentiating_value$',
        views.ViewLeadDistinguishingValue.as_view(),
        name='view_lead_distinguishing_value'),
    url(r'^lead/(?P<lead_id>\d+)/opportunities$',
        views.ViewLeadOpportunities.as_view(),
        name='view_lead_opportunities'),

    url(r'^lead/(?P<lead_id>\d+)/differentiating_value/new$',
        views.AddDistinguishingValueChallenge.as_view(),
        name='add_lead_distinguishing_value_challenge'),
    url(r'^lead/(?P<lead_id>\d+)/differentiating_value/(?P<dvc_id>\d+)/update$',
        views.UpdateDistinguishingValueChallenge.as_view(),
        name='update_distinguishing_value_challenge'),
    url(r'^lead/(?P<lead_id>\d+)/differentiating_value/(?P<dvc_id>\d+)/delete$',
        views.DeleteDistinguishingValueChallenge.as_view(),
        name='delete_distinguishing_value_challenge'),
    url(r'^lead/(?P<lead_id>\d+)/differentiating_value/add-template-dvs$',
        views.AddTemplateDifferentiatingValues.as_view(),
        name='add_template_differentiating_values'),

    url(r'^lead/(?P<lead_id>\d+)/opportunity/new$',
        views.CreateOpportunity.as_view(),
        name='add_lead_opportunity'),
    url(r'^lead/(?P<lead_id>\d+)/opportunity/(?P<opportunity_id>\d+)/update$',
        views.EditOpportunity.as_view(),
        name='edit_lead_opportunity'),
    url(r'^lead/(?P<lead_id>\d+)/opportunity/(?P<opportunity_id>\d+)/delete$',
        views.DeleteOpportunity.as_view(),
        name='delete_lead_opportunity'),


    # Add Lead Note
    url(r'^lead/(?P<lead_id>\d+)/add_note$',
        views.AddLeadNote.as_view(),
        name='add_lead_note'),
    # Get Tags / Add Tag
    url(r'^lead/(?P<lead_id>\d+)/tags/$',
        views.LeadTags.as_view(),
        name='lead_tags'),
    # Remove Tag
    url(r'^lead/(?P<lead_id>\d+)/tags/remove$',
        views.RemoveLeadTag.as_view(),
        name='remove_lead_tag'),
    url(r'^lead/(?P<lead_id>\d+)/add-attachment$', # expects querystring of transition_id=<int>
        views.lead_upload_attachment,
        name='add_lead_attachment'),
    url(r'^lead/(?P<lead_id>\d+)/download-attachment/(?P<attachment_id>\w+)/$',
        views.lead_download_attachment,
        name='download_lead_attachment'),
    # Add Contact
    url(r'^lead/(?P<lead_id>\d+)/add-contact$',
        views.AddLeadContact.as_view(),
        name='lead_add_contact'),
    # Remove Contact
    url(r'^lead/(?P<lead_id>\d+)/remove-contact$',
        views.RemoveLeadContact.as_view(),
        name='lead_remove_contact'),

    # Add General Task
    url(r'^lead/(?P<lead_id>\d+)/add-general-task$',
        views.AddLeadGeneralTask.as_view(),
        name='lead_add_general_task'),
    # Remove General Task
    url(r'^lead/(?P<lead_id>\d+)/remove-general-task$',
        views.RemoveLeadGeneralTask.as_view(),
        name='lead_remove_general_task'),

    # Template Differentiating Values
    url(r'^differentiating_value/$',
        views.ListTemplateDifferentiatingValue.as_view(),
        name='list_template_differentiating_values'),
    url(r'^differentiating_value/create/$',
        views.CreateTemplateDifferentiatingValue.as_view(),
        name='create_template_differentiating_value'),
    url(r'^differentiating_value/(?P<template_dv_id>\d+)/edit$',
        views.EditTemplateDifferentiatingValue.as_view(),
        name='edit_template_differentiating_value'),
    url(r'^differentiating_value/(?P<template_dv_id>\d+)/delete$',
        views.DeleteTemplateDifferentiatingValue.as_view(),
        name='delete_template_differentiating_value'),

    # Lead Differentiating Value Cost Items
    url(r'^lead/(?P<lead_id>\d+)/differentiating_value/(?P<dvc_id>\d+)/cost_item/create$',
        views.CreateDVCostItem.as_view(),
        name='create_dv_cost_item'),
    url(r'^lead/(?P<lead_id>\d+)/differentiating_value/(?P<dvc_id>\d+)/cost_item/(?P<cost_item_id>\d+)/edit$',
        views.EditDVCostItem.as_view(),
        name='edit_dv_cost_item'),
    url(r'^lead/(?P<lead_id>\d+)/differentiating_value/(?P<dvc_id>\d+)/cost_item/(?P<cost_item_id>\d+)/delete$',
        views.DeleteDVCostItem.as_view(),
        name='delete_dv_cost_item'),
)
