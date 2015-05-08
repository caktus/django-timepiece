from django.conf.urls import url

from timepiece.crm import views


urlpatterns = [
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
    url(r'^user/(?P<user_id>\d+)/delete/$',
        views.DeleteUser.as_view(),
        name='delete_user'),

    # User timesheets
    url(r'^user/(?P<user_id>\d+)/timesheet/'
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

    # Project timesheets
    url(r'^project/(?P<project_id>\d+)/timesheet/$',
        views.ProjectTimesheet.as_view(),
        name='view_project_timesheet'),
    url(r'^project/(?P<project_id>\d+)/timesheet/csv/$',
        views.ProjectTimesheetCSV.as_view(),
        name='view_project_timesheet_csv'),

    # Businesses
    url(r'^business/$',
        views.ListBusinesses.as_view(),
        name='list_businesses'),
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
]
