import datetime
from dateutil.relativedelta import relativedelta
import json
import urllib

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse, reverse_lazy
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import (CreateView, DeleteView, DetailView,
        UpdateView, FormView, View, TemplateView)

from timepiece import utils
from timepiece.forms import YearMonthForm
from timepiece.templatetags.timepiece_tags import seconds_to_hours
from timepiece.utils import add_timezone
from timepiece.utils.csv import CSVViewMixin, ExtendedJSONEncoder
from timepiece.utils.cbv import cbv_decorator, PermissionsRequiredMixin
from timepiece.utils.search import SearchListView

from timepiece.crm.forms import (CreateEditBusinessForm, CreateEditProjectForm,
        EditUserSettingsForm, EditProjectRelationshipForm, SelectProjectForm,
        EditUserForm, CreateUserForm, SelectUserForm, ProjectSearchForm,
        QuickSearchForm, TimesheetSelectMonthForm)
from timepiece.crm.models import Business, Project, ProjectRelationship
from timepiece.entries.models import Entry


# Search


@cbv_decorator(login_required)
class QuickSearch(FormView):
    form_class = QuickSearchForm
    template_name = 'timepiece/quick_search.html'

    def form_valid(self, form):
        return HttpResponseRedirect(form.get_result())


# User timesheets


class UserTimesheetMixin(object):
    """Checks permission & evaluates the month form for timesheet views."""
    form_class = TimesheetSelectMonthForm

    def dispatch(self, request, user_id, *args, **kwargs):
        # If the user does not have an administrative permission, they may
        # only view their own timesheet.
        self.timesheet_user = get_object_or_404(User, pk=user_id)
        if not request.user == self.timesheet_user:
            if not request.user.has_perm('entries.view_entry_summary'):
                raise PermissionDenied

        self.month_form = self.form_class(data=request.GET or None)
        self.this_month = self.month_form.get_month_start()

        return super(UserTimesheetMixin, self).dispatch(request, *args, **kwargs)


@cbv_decorator(login_required)
class ViewUserTimesheet(UserTimesheetMixin, TemplateView):
    """Renders basic data for the monthly timesheet.

    Backbone.js is used to retrieve the month's entries through the
    ViewUserTimesheetAjax view.
    """
    template_name = 'timepiece/user/timesheet/view.html'

    def get_context_data(self, active_tab=None, **kwargs):
        return {
            'active_tab': active_tab or 'all-entries',
            'month_form': self.month_form,
            'last_month': self.this_month - relativedelta(months=1),
            'next_month': self.this_month + relativedelta(months=1),
            'this_month': self.this_month,
            'timesheet_user': self.timesheet_user,
        }


# Not using login_required here to avoid redirecting an AJAX request.
# The logic in UserTimesheetMixin.dispatch prevents unauthenticated access.
class ViewUserTimesheetAjax(UserTimesheetMixin, View):
    """AJAX view for Backbone to retrieve entries for the monthly timesheet."""

    def get(self, request, *args, **kwargs):
        data = {
            'entries': self.get_month_entries(),
            'weeks': self.get_weeks(),
            'this_month': self.this_month,
            'last_month': self.this_month - relativedelta(months=1),
            'next_month': self.this_month + relativedelta(months=1),
            'verify_url': reverse('verify_entries'),
            'reject_url': reverse('reject_entries'),
            'approve_url': reverse('approve_entries'),
        }
        return HttpResponse(json.dumps(data, cls=ExtendedJSONEncoder),
                content_type='application/json')

    def get_weeks(self):
        start, end = self.month_form.get_extended_month_range()
        weeks = []
        cursor = start
        while cursor < end:
            next_week = cursor + relativedelta(days=7)
            weeks.append((
                add_timezone(cursor),
                add_timezone(next_week - relativedelta(microseconds=1)),
            ))
            cursor = next_week
        return weeks

    def get_month_entries(self):
        """
        Return a list of summaries of the entries in the month's extended date
        range, ordered by end_time.
        """
        start, end = self.month_form.get_extended_month_range()
        entries = Entry.objects.filter(user=self.timesheet_user)
        entries = entries.filter(end_time__range=(start, end))
        entries = entries.order_by('end_time')
        return entries.summaries()


# Project timesheets


class ProjectTimesheet(PermissionsRequiredMixin, DetailView):
    template_name = 'timepiece/project/timesheet.html'
    model = Project
    permissions = ('entries.view_project_time_sheet',)
    context_object_name = 'project'
    pk_url_kwarg = 'project_id'

    def get(self, *args, **kwargs):
        if 'csv' in self.request.GET:
            request_get = self.request.GET.copy()
            request_get.pop('csv')
            return_url = reverse('view_project_timesheet_csv',
                                 args=(self.get_object().pk,))
            return_url += '?%s' % urllib.urlencode(request_get)
            return redirect(return_url)
        return super(ProjectTimesheet, self).get(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ProjectTimesheet, self).get_context_data(**kwargs)
        project = self.object
        year_month_form = YearMonthForm(self.request.GET or None)
        if self.request.GET and year_month_form.is_valid():
            from_date, to_date = year_month_form.save()
        else:
            date = utils.add_timezone(datetime.datetime.today())
            from_date = utils.get_month_start(date).date()
            to_date = from_date + relativedelta(months=1)
        entries_qs = Entry.objects
        entries_qs = entries_qs.timespan(from_date, span='month').filter(
            project=project
        )
        extra_values = ('start_time', 'end_time', 'comments', 'seconds_paused',
                'id', 'location__name', 'project__name', 'activity__name',
                'status')
        month_entries = entries_qs.date_trunc('month', extra_values)
        total = entries_qs.aggregate(hours=Sum('hours'))['hours']
        user_entries = entries_qs.order_by().values(
            'user__first_name', 'user__last_name').annotate(
            sum=Sum('hours')).order_by('-sum'
        )
        activity_entries = entries_qs.order_by().values(
            'activity__name').annotate(
            sum=Sum('hours')).order_by('-sum'
        )
        context.update({
            'project': project,
            'year_month_form': year_month_form,
            'from_date': from_date,
            'to_date': to_date - relativedelta(days=1),
            'entries': month_entries,
            'total': total,
            'user_entries': user_entries,
            'activity_entries': activity_entries,
        })
        return context


class ProjectTimesheetCSV(CSVViewMixin, ProjectTimesheet):

    def get_filename(self, context):
        project = self.object.name
        to_date_str = context['to_date'].strftime('%m-%d-%Y')
        return 'Project_timesheet {0} {1}'.format(project, to_date_str)

    def convert_context_to_csv(self, context):
        rows = []
        rows.append([
            'Date',
            'User',
            'Activity',
            'Location',
            'Time In',
            'Time Out',
            'Breaks',
            'Hours',
        ])
        for entry in context['entries']:
            data = [
                entry['start_time'].strftime('%x'),
                entry['user__first_name'] + ' ' + entry['user__last_name'],
                entry['activity__name'],
                entry['location__name'],
                entry['start_time'].strftime('%X'),
                entry['end_time'].strftime('%X'),
                seconds_to_hours(entry['seconds_paused']),
                entry['hours'],
            ]
            rows.append(data)
        total = context['total']
        rows.append(('', '', '', '', '', '', 'Total:', total))
        return rows


# Businesses


class ListBusinesses(PermissionsRequiredMixin, SearchListView):
    model = Business
    permissions = ('crm.view_business',)
    redirect_if_one_result = True
    search_fields = ['name__icontains', 'description__icontains']
    template_name = 'timepiece/business/list.html'


class ViewBusiness(PermissionsRequiredMixin, DetailView):
    model = Business
    pk_url_kwarg = 'business_id'
    template_name = 'timepiece/business/view.html'
    permissions = ('crm.view_business',)


class CreateBusiness(PermissionsRequiredMixin, CreateView):
    model = Business
    form_class = CreateEditBusinessForm
    template_name = 'timepiece/business/create_edit.html'
    permissions = ('crm.add_business',)


class DeleteBusiness(PermissionsRequiredMixin, DeleteView):
    model = Business
    success_url = reverse_lazy('list_businesses')
    permissions = ('crm.delete_business',)
    pk_url_kwarg = 'business_id'
    template_name = 'timepiece/delete_object.html'


class EditBusiness(PermissionsRequiredMixin, UpdateView):
    model = Business
    form_class = CreateEditBusinessForm
    template_name = 'timepiece/business/create_edit.html'
    permissions = ('crm.change_business',)
    pk_url_kwarg = 'business_id'


# Users


@cbv_decorator(login_required)
class EditSettings(UpdateView):
    form_class = EditUserSettingsForm
    template_name = 'timepiece/user/settings.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        messages.info(self.request, 'Your settings have been updated.')
        return self.request.REQUEST.get('next', None) or reverse('dashboard')


class ListUsers(PermissionsRequiredMixin, SearchListView):
    model = User
    permissions = ('auth.view_user',)
    redirect_if_one_result = True
    search_fields = ['first_name__icontains', 'last_name__icontains',
            'email__icontains', 'username__icontains']
    template_name = 'timepiece/user/list.html'

    def get_queryset(self):
        return super(ListUsers, self).get_queryset().select_related()


class ViewUser(PermissionsRequiredMixin, DetailView):
    model = User
    pk_url_kwarg = 'user_id'
    template_name = 'timepiece/user/view.html'
    permissions = ('auth.view_user',)

    def get_context_data(self, **kwargs):
        kwargs.update({'add_project_form': SelectProjectForm()})
        return super(ViewUser, self).get_context_data(**kwargs)


class CreateUser(PermissionsRequiredMixin, CreateView):
    model = User
    form_class = CreateUserForm
    template_name = 'timepiece/user/create_edit.html'
    permissions = ('auth.add_user',)


class DeleteUser(PermissionsRequiredMixin, DeleteView):
    model = User
    success_url = reverse_lazy('list_users')
    permissions = ('auth.delete_user',)
    pk_url_kwarg = 'user_id'
    template_name = 'timepiece/delete_object.html'


class EditUser(PermissionsRequiredMixin, UpdateView):
    model = User
    form_class = EditUserForm
    template_name = 'timepiece/user/create_edit.html'
    permissions = ('auth.change_user',)
    pk_url_kwarg = 'user_id'


# Projects


class ListProjects(PermissionsRequiredMixin, SearchListView):
    model = Project
    form_class = ProjectSearchForm
    permissions = ['crm.view_project']
    redirect_if_one_result = True
    search_fields = ['name__icontains', 'description__icontains']
    template_name = 'timepiece/project/list.html'

    def filter_form_valid(self, form, queryset):
        queryset = super(ListProjects, self).filter_form_valid(form, queryset)
        status = form.cleaned_data['status']
        if status:
            queryset = queryset.filter(status=status)
        return queryset


class ViewProject(PermissionsRequiredMixin, DetailView):
    model = Project
    pk_url_kwarg = 'project_id'
    template_name = 'timepiece/project/view.html'
    permissions = ('crm.view_project',)

    def get_context_data(self, **kwargs):
        kwargs.update({'add_user_form': SelectUserForm()})
        return super(ViewProject, self).get_context_data(**kwargs)


class CreateProject(PermissionsRequiredMixin, CreateView):
    model = Project
    form_class = CreateEditProjectForm
    permissions = ('crm.add_project',)
    template_name = 'timepiece/project/create_edit.html'


class DeleteProject(PermissionsRequiredMixin, DeleteView):
    model = Project
    success_url = reverse_lazy('list_projects')
    permissions = ('crm.delete_project',)
    pk_url_kwarg = 'project_id'
    template_name = 'timepiece/delete_object.html'


class EditProject(PermissionsRequiredMixin, UpdateView):
    model = Project
    form_class = CreateEditProjectForm
    permissions = ('crm.change_project',)
    template_name = 'timepiece/project/create_edit.html'
    pk_url_kwarg = 'project_id'


# User-project relationships


@cbv_decorator(csrf_exempt)
@cbv_decorator(transaction.commit_on_success)
class CreateRelationship(PermissionsRequiredMixin, View):
    permissions = ('crm.add_projectrelationship',)

    def post(self, request, *args, **kwargs):
        user = self.get_user()
        project = self.get_project()
        if user and project:
            ProjectRelationship.objects.get_or_create(user=user, project=project)
        redirect_to = request.REQUEST.get('next', None) or reverse('dashboard')
        return HttpResponseRedirect(redirect_to)

    def get_user(self):
        user_id = self.request.REQUEST.get('user_id', None)
        if user_id:
            return get_object_or_404(User, pk=user_id)
        return SelectUserForm(self.request.POST).get_user()

    def get_project(self):
        project_id = self.request.REQUEST.get('project_id', None)
        if project_id:
            return get_object_or_404(Project, pk=project_id)
        return SelectProjectForm(self.request.POST).get_project()


class RelationshipObjectMixin(object):
    """Handles retrieving and redirecting for ProjectRelationship objects."""

    def get_object(self, queryset=None):
        queryset = self.get_queryset() if queryset is None else queryset
        user_id = self.request.REQUEST.get('user_id', None)
        project_id = self.request.REQUEST.get('project_id', None)
        return get_object_or_404(self.model, user__id=user_id,
                project__id=project_id)

    def get_success_url(self):
        return self.request.REQUEST.get('next',
                self.object.project.get_absolute_url())


@cbv_decorator(transaction.commit_on_success)
class EditRelationship(PermissionsRequiredMixin, RelationshipObjectMixin,
        UpdateView):
    model = ProjectRelationship
    permissions = ('crm.change_projectrelationship',)
    template_name = 'timepiece/relationship/edit.html'
    form_class = EditProjectRelationshipForm


@cbv_decorator(csrf_exempt)
@cbv_decorator(transaction.commit_on_success)
class DeleteRelationship(PermissionsRequiredMixin, RelationshipObjectMixin,
        DeleteView):
    model = ProjectRelationship
    permissions = ('crm.delete_projectrelationship',)
    template_name = 'timepiece/relationship/delete.html'
