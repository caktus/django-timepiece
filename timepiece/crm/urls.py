from django.urls import re_path

from timepiece.crm import views


urlpatterns = [
    # Search
    re_path(r'^quick_search/$',
            views.QuickSearch.as_view(),
            name='quick_search'),

    # Users
    re_path(r'^user/settings/$',
            views.EditSettings.as_view(),
            name='edit_settings'),
    re_path(r'^user/$',
            views.ListUsers.as_view(),
            name='list_users'),
    re_path(r'^user/create/$',
            views.CreateUser.as_view(),
            name='create_user'),
    re_path(r'^user/(?P<user_id>\d+)/$',
            views.ViewUser.as_view(),
            name='view_user'),
    re_path(r'^user/(?P<user_id>\d+)/edit/$',
            views.EditUser.as_view(),
            name='edit_user'),
    re_path(r'^user/(?P<user_id>\d+)/delete/$',
            views.DeleteUser.as_view(),
            name='delete_user'),

    # User timesheets
    re_path(
        r'^user/(?P<user_id>\d+)/timesheet/(?:(?P<active_tab>overview|all-entries|daily-summary)/)?$',
        views.view_user_timesheet,
        name='view_user_timesheet'),
    re_path(r'^user/(?P<user_id>\d+)/timesheet/reject/$',
            views.reject_user_timesheet,
            name='reject_user_timesheet'),
    re_path(r'^user/(?P<user_id>\d+)/timesheet/(?P<action>verify|approve)/$',
            views.change_user_timesheet,
            name='change_user_timesheet'),

    # Projects
    re_path(r'^project/$',
            views.ListProjects.as_view(),
            name='list_projects'),
    re_path(r'^project/create/$',
            views.CreateProject.as_view(),
            name='create_project'),
    re_path(r'^project/(?P<project_id>\d+)/$',
            views.ViewProject.as_view(),
            name='view_project'),
    re_path(r'^project/(?P<project_id>\d+)/edit/$',
            views.EditProject.as_view(),
            name='edit_project'),
    re_path(r'^project/(?P<project_id>\d+)/delete/$',
            views.DeleteProject.as_view(),
            name='delete_project'),

    # Project timesheets
    re_path(r'^project/(?P<project_id>\d+)/timesheet/$',
            views.ProjectTimesheet.as_view(),
            name='view_project_timesheet'),
    re_path(r'^project/(?P<project_id>\d+)/timesheet/csv/$',
            views.ProjectTimesheetCSV.as_view(),
            name='view_project_timesheet_csv'),

    # Businesses
    re_path(r'^business/$',
            views.ListBusinesses.as_view(),
            name='list_businesses'),
    re_path(r'^business/create/$',
            views.CreateBusiness.as_view(),
            name='create_business'),
    re_path(r'^business/(?P<business_id>\d+)/$',
            views.ViewBusiness.as_view(),
            name='view_business'),
    re_path(r'^business/(?P<business_id>\d+)/edit/$',
            views.EditBusiness.as_view(),
            name='edit_business'),
    re_path(r'^business/(?P<business_id>\d+)/delete/$',
            views.DeleteBusiness.as_view(),
            name='delete_business'),

    # User-project relationships
    re_path(r'^relationship/create/$',
            views.CreateRelationship.as_view(),
            name='create_relationship'),
    re_path(r'^relationship/edit/$',
            views.EditRelationship.as_view(),
            name='edit_relationship'),
    re_path(r'^relationship/delete/$',
            views.DeleteRelationship.as_view(),
            name='delete_relationship'),
]
