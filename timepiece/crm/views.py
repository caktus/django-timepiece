import datetime
from dateutil.relativedelta import relativedelta
import urllib
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse, reverse_lazy
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import (CreateView, DeleteView, DetailView,
        UpdateView, FormView, View)

from timepiece import utils
from timepiece.forms import YearMonthForm, UserYearMonthForm
from timepiece.templatetags.timepiece_tags import seconds_to_hours
from timepiece.utils.csv import CSVViewMixin
from timepiece.utils.search import SearchListView
from timepiece.utils.views import cbv_decorator

from timepiece.crm.forms import (CreateEditBusinessForm, CreateEditProjectForm,
        EditUserSettingsForm, EditProjectRelationshipForm, SelectProjectForm,
        EditUserForm, CreateUserForm, SelectUserForm, ProjectSearchForm,
        QuickSearchForm, CreateEditPTORequestForm, CreateEditMilestoneForm,
        CreateEditActivityGoalForm, ApproveDenyPTORequestForm)
from timepiece.crm.models import (Business, Project, ProjectRelationship, UserProfile,
    PaidTimeOffLog, PaidTimeOffRequest, Milestone, ActivityGoal)
from timepiece.crm.utils import grouped_totals
from timepiece.entries.models import Entry, Activity, Location

from holidays.models import Holiday
from . import emails


@cbv_decorator(login_required)
class QuickSearch(FormView):
    form_class = QuickSearchForm
    template_name = 'timepiece/quick_search.html'

    def form_valid(self, form):
        return HttpResponseRedirect(form.get_result())


# User timesheets


@permission_required('entries.view_payroll_summary')
def reject_user_timesheet(request, user_id):
    """
    This allows admins to reject all entries, instead of just one
    """
    from_date = request.GET.get('from_date', None) or request.POST.get('from_date', None)
    (year, month, day) = from_date.split('-')
    if int(day) <= 15:
        half =1
    else:
        half = 2
    print 'year', int(year), 'month', int(month), 'half', int(half)
    form = YearMonthForm({'year':int(year), 'month':int(month), 'half':half})
    user = User.objects.get(pk=user_id)
    if form.is_valid():
        from_date, to_date = form.save()
        entries = Entry.no_join.filter(status=Entry.VERIFIED, user=user,
            start_time__gte=from_date, end_time__lte=to_date)
        if request.POST.get('yes'):
            if entries.exists():
                count = entries.count()
                entries.update(status=Entry.UNVERIFIED)
                msg = 'You have rejected %d previously verified entries.' \
                    % count
            else:
                msg = 'There are no verified entries to reject.'
            messages.info(request, msg)
        else:
            return render(request, 'timepiece/user/timesheet/reject.html', {
                'from_date': from_date,
                'to_date': to_date,
                'to_date_label': to_date + datetime.timedelta(days=-1),
                'timesheet_user': user
            })
    else:
        msg = 'You must provide a month and year for entries to be rejected.'
        messages.error(request, msg)

    url = reverse('view_user_timesheet', args=(user_id,))
    return HttpResponseRedirect(url)


@login_required
def view_user_timesheet(request, user_id, active_tab):
    # User can only view their own time sheet unless they have a permission.
    user = get_object_or_404(User, pk=user_id)
    has_perm = request.user.has_perm('entries.view_entry_summary')
    if not (has_perm or user.pk == request.user.pk):
        return HttpResponseForbidden('Forbidden')

    FormClass = UserYearMonthForm if has_perm else YearMonthForm
    form = FormClass(request.GET or None)
    if form.is_valid():
        if has_perm:
            from_date, to_date, form_user = form.save()
            if form_user and request.GET.get('yearmonth', None):
                # Redirect to form_user's time sheet.
                # Do not use request.GET in urlencode to prevent redirect
                # loop caused by yearmonth parameter.
                url = reverse('view_user_timesheet', args=(form_user.pk,))
                request_data = {
                    'half': 1 if from_date.day <= 15 else 2,
                    'month': from_date.month,
                    'year': from_date.year,
                    'user': form_user.pk,  # Keep so that user appears in form.
                }
                url += '?{0}'.format(urllib.urlencode(request_data))
                return HttpResponseRedirect(url)
        else:  # User must be viewing their own time sheet; no redirect needed.
            from_date, to_date = form.save()
        from_date = utils.add_timezone(from_date)
        to_date = utils.add_timezone(to_date)
    else:
        # Default to showing current bi-monthly period.
        from_date, to_date = utils.get_bimonthly_dates(datetime.date.today())
    entries_qs = Entry.objects.filter(user=user)
    # DBROWNE - CHANGED THIS TO MATCH THE DESIRED RESULT FOR AAC ENGINEERING
    #month_qs = entries_qs.timespan(from_date, span='month')
    month_qs = entries_qs.timespan(from_date, to_date=to_date)
    extra_values = ('start_time', 'end_time', 'comments', 'seconds_paused',
            'id', 'location__name', 'project__name', 'activity__name',
            'status', 'mechanism')
    month_entries = month_qs.date_trunc('month', extra_values)
    # For grouped entries, back date up to the start of the period.
    first_week = utils.get_period_start(from_date)
    month_week = first_week + relativedelta(weeks=1)
    grouped_qs = entries_qs.timespan(first_week, to_date=to_date)
    intersection = grouped_qs.filter(start_time__lt=month_week,
        start_time__gte=from_date)
    # If the month of the first week starts in the previous
    # month and we dont have entries in that previous ISO
    # week, then update the first week to start at the first
    # of the actual month
    if not intersection and first_week.month < from_date.month:
        grouped_qs = entries_qs.timespan(from_date, to_date=to_date)
    totals = grouped_totals(grouped_qs) if month_entries else ''
    project_entries = month_qs.order_by().values(
        'project__name').annotate(sum=Sum('hours')).order_by('-sum')
    summary = Entry.summary(user, from_date, to_date)

    show_approve = show_verify = False
    can_change = request.user.has_perm('entries.change_entry')
    can_approve = request.user.has_perm('entries.approve_timesheet')
    if can_change or can_approve or user == request.user:
        statuses = list(month_qs.values_list('status', flat=True))
        total_statuses = len(statuses)
        unverified_count = statuses.count(Entry.UNVERIFIED)
        verified_count = statuses.count(Entry.VERIFIED)
        approved_count = statuses.count(Entry.APPROVED)
    if can_change or user == request.user:
        show_verify = unverified_count != 0
    if can_approve:
        show_approve = verified_count + approved_count == total_statuses \
                and verified_count > 0 and total_statuses != 0
    
    # # TODO: for some reason I have to loop over this in order to
    # # remedy an error... does not make any sense
    # for gt in totals:
    #     gt = gt
    # for week, week_totals, days in totals:
    #         print 'week', week, 'week_totals', week_totals, 'days', days
    return render(request, 'timepiece/user/timesheet/view.html', {
        'active_tab': active_tab or 'overview',
        'year_month_form': form,
        'from_date': from_date,
        'to_date': to_date - relativedelta(days=1),
        'show_verify': show_verify,
        'show_approve': show_approve,
        'timesheet_user': user,
        'entries': month_entries,
        'grouped_totals': totals,
        'project_entries': project_entries,
        'summary': summary,
    })


@login_required
def change_user_timesheet(request, user_id, action):
    user = get_object_or_404(User, pk=user_id)
    admin_verify = request.user.has_perm('entries.view_entry_summary')
    perm = True

    if not admin_verify and action == 'verify' and user != request.user:
        perm = False
    if not admin_verify and action == 'approve':
        perm = False

    if not perm:
        return HttpResponseForbidden('Forbidden: You cannot {0} this '
                'timesheet.'.format(action))

    try:
        from_date = request.GET.get('from_date')
        from_date = utils.add_timezone(
            datetime.datetime.strptime(from_date, '%Y-%m-%d'))
    except (ValueError, OverflowError, KeyError):
        raise Http404
    #to_date = from_date + relativedelta(months=1)
    from_date, to_date = utils.get_bimonthly_dates(from_date)
    entries = Entry.no_join.filter(user=user_id,
                                   end_time__gte=from_date,
                                   end_time__lt=to_date)
    active_entries = Entry.no_join.filter(
        user=user_id,
        start_time__lt=to_date,
        end_time=None,
        status=Entry.UNVERIFIED,
    )
    filter_status = {
        'verify': Entry.UNVERIFIED,
        'approve': Entry.VERIFIED,
    }
    entries = entries.filter(status=filter_status[action])

    return_url = reverse('view_user_timesheet', args=(user_id,))
    return_url += '?%s' % urllib.urlencode({
        'year': from_date.year,
        'month': from_date.month,
        'half': 1 if from_date.day <= 15 else 2,
    })
    if active_entries:
        msg = 'You cannot verify/approve this timesheet while the user {0} ' \
            'has an active entry. Please have them close any active ' \
            'entries.'.format(user.get_name_or_username())
        messages.error(request, msg)
        return redirect(return_url)
    if request.POST.get('do_action') == 'Yes':
        update_status = {
            'verify': 'verified',
            'approve': 'approved',
        }
        entries.update(status=update_status[action])
        messages.info(request,
            'Your entries have been %s' % update_status[action])
        return redirect(return_url)
    hours = entries.all().aggregate(s=Sum('hours'))['s']
    if not hours:
        msg = 'You cannot verify/approve a timesheet with no hours'
        messages.error(request, msg)
        return redirect(return_url)
    return render(request, 'timepiece/user/timesheet/change.html', {
        'action': action,
        'timesheet_user': user,
        'from_date': from_date,
        'to_date': to_date - relativedelta(days=1),
        'return_url': return_url,
        'hours': hours,
    })


# Project timesheets


@cbv_decorator(permission_required('entries.view_project_timesheet'))
class ProjectTimesheet(DetailView):
    template_name = 'timepiece/project/timesheet.html'
    model = Project
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
        from_datetime = datetime.datetime.combine(from_date, 
            datetime.datetime.min.time())
        to_datetime = datetime.datetime.combine(to_date,
            datetime.datetime.max.time())
        entries_qs = Entry.objects.filter(start_time__gte=from_datetime,
                                          end_time__lt=to_datetime,
                                          project=project)
        # entries_qs = entries_qs.timespan(from_date, span='month').filter(
        #     project=project
        # )
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


@cbv_decorator(permission_required('crm.view_business'))
class ListBusinesses(SearchListView):
    model = Business
    redirect_if_one_result = True
    search_fields = ['name__icontains', 'description__icontains']
    template_name = 'timepiece/business/list.html'


@cbv_decorator(permission_required('crm.view_business'))
class ViewBusiness(DetailView):
    model = Business
    pk_url_kwarg = 'business_id'
    template_name = 'timepiece/business/view.html'


@cbv_decorator(permission_required('crm.add_business'))
class CreateBusiness(CreateView):
    model = Business
    form_class = CreateEditBusinessForm
    template_name = 'timepiece/business/create_edit.html'


@cbv_decorator(permission_required('crm.delete_business'))
class DeleteBusiness(DeleteView):
    model = Business
    success_url = reverse_lazy('list_businesses')
    pk_url_kwarg = 'business_id'
    template_name = 'timepiece/delete_object.html'


@cbv_decorator(permission_required('crm.change_business'))
class EditBusiness(UpdateView):
    model = Business
    form_class = CreateEditBusinessForm
    template_name = 'timepiece/business/create_edit.html'
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


@cbv_decorator(permission_required('auth.view_user'))
class ListUsers(SearchListView):
    model = User
    redirect_if_one_result = True
    search_fields = ['first_name__icontains', 'last_name__icontains',
            'email__icontains', 'username__icontains']
    template_name = 'timepiece/user/list.html'

    def get_queryset(self):
        return super(ListUsers, self).get_queryset().select_related()


@cbv_decorator(permission_required('auth.view_user'))
class ViewUser(DetailView):
    model = User
    pk_url_kwarg = 'user_id'
    template_name = 'timepiece/user/view.html'

    def get_context_data(self, **kwargs):
        kwargs.update({'add_project_form': SelectProjectForm()})
        return super(ViewUser, self).get_context_data(**kwargs)


@cbv_decorator(permission_required('auth.add_user'))
class CreateUser(CreateView):
    model = User
    form_class = CreateUserForm
    template_name = 'timepiece/user/create_edit.html'


@cbv_decorator(permission_required('auth.delete_user'))
class DeleteUser(DeleteView):
    model = User
    success_url = reverse_lazy('list_users')
    pk_url_kwarg = 'user_id'
    template_name = 'timepiece/delete_object.html'

    def delete(self, request, *args, **kwargs):
        up = UserProfile.objects.get(user__id=int(kwargs['user_id']))
        up.delete()
        return super(DeleteUser, self).delete(request, *args, **kwargs)


@cbv_decorator(permission_required('auth.change_user'))
class EditUser(UpdateView):
    model = User
    form_class = EditUserForm
    template_name = 'timepiece/user/create_edit.html'
    pk_url_kwarg = 'user_id'


# Projects


@cbv_decorator(permission_required('crm.view_project'))
class ListProjects(SearchListView):
    model = Project
    form_class = ProjectSearchForm
    redirect_if_one_result = True
    search_fields = ['name__icontains', 'description__icontains', 'code__icontains',
    'point_person__first_name__icontains', 'point_person__last_name__icontains']
    template_name = 'timepiece/project/list.html'

    def filter_form_valid(self, form, queryset):
        queryset = super(ListProjects, self).filter_form_valid(form, queryset)
        status = form.cleaned_data['status']
        if status:
            queryset = queryset.filter(status=status)
        return queryset


@cbv_decorator(permission_required('crm.view_project'))
class ViewProject(DetailView):
    model = Project
    pk_url_kwarg = 'project_id'
    template_name = 'timepiece/project/view.html'

    def get_context_data(self, **kwargs):
        kwargs.update({'add_user_form': SelectUserForm()})
        return super(ViewProject, self).get_context_data(**kwargs)


@cbv_decorator(permission_required('crm.add_project'))
class CreateProject(CreateView):
    model = Project
    form_class = CreateEditProjectForm
    template_name = 'timepiece/project/create_edit.html'


@cbv_decorator(permission_required('crm.delete_project'))
class DeleteProject(DeleteView):
    model = Project
    success_url = reverse_lazy('list_projects')
    pk_url_kwarg = 'project_id'
    template_name = 'timepiece/delete_object.html'


@cbv_decorator(permission_required('crm.change_project'))
class EditProject(UpdateView):
    model = Project
    form_class = CreateEditProjectForm
    template_name = 'timepiece/project/create_edit.html'
    pk_url_kwarg = 'project_id'


# User-project relationships


@cbv_decorator(permission_required('crm.add_projectrelationship'))
@cbv_decorator(csrf_exempt)
@cbv_decorator(transaction.commit_on_success)
class CreateRelationship(View):

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


@cbv_decorator(permission_required('crm.change_projectrelationship'))
@cbv_decorator(transaction.commit_on_success)
class EditRelationship(RelationshipObjectMixin, UpdateView):
    model = ProjectRelationship
    template_name = 'timepiece/relationship/edit.html'
    form_class = EditProjectRelationshipForm


@cbv_decorator(permission_required('crm.delete_projectrelationship'))
@cbv_decorator(csrf_exempt)
@cbv_decorator(transaction.commit_on_success)
class DeleteRelationship(RelationshipObjectMixin, DeleteView):
    model = ProjectRelationship
    template_name = 'timepiece/relationship/delete.html'

@login_required
def get_users_for_business(request, business_id):
    data = {}
    if request.user.groups.filter(id=1).count() or request.user.is_superuser:
        business = Business.objects.get(id=int(business_id))
        for up in UserProfile.objects.filter(business=business):
            data[up.user.id] = {'email': up.user.email,
                                'username': up.user.username,
                                'name': '%s %s' % (up.user.first_name, up.user.last_name)}
    return HttpResponse(json.dumps(data),
                        content_type='application/json')

@login_required
def get_project_activities(request, project_id):
    data = []
    try:
        project = Project.objects.get(id=int(project_id))
        if project.activity_group:
            for activity in project.activity_group.activities.values():
                data.append(activity)
        else:
            for activity in Activity.objects.all().order_by('name'):
                data.append(activity.get_json())
    except:
        for activity in Activity.objects.all().order_by('name'):
            data.append(activity.get_json())
    return HttpResponse(json.dumps(data),
                        content_type='application/json')


#@cbv_decorator(permission_required('crm.view_business'))
@login_required
def pto_home(request, active_tab='summary'):
    data = {}
    data['user_profile'] = UserProfile.objects.get(user=request.user)
    data['pto_requests'] = PaidTimeOffRequest.objects.filter(user_profile=data['user_profile']).order_by('-pto_start_date')
    data['pto_log'] = PaidTimeOffLog.objects.filter(user_profile=data['user_profile'])
    if request.user.has_perm('crm.can_approve_pto_requests'):
        data['pto_approvals'] = PaidTimeOffRequest.objects.filter(approver=None)
        data['pto_all_history'] = PaidTimeOffLog.objects.filter().order_by('user_profile', '-date')
        data['all_pto_requests'] = PaidTimeOffRequest.objects.all().order_by('-request_date')
    if active_tab:
        data['active_tab'] = active_tab
    else:
        data['active_tab'] = 'summary'

    this_year = datetime.date.today().year
    data['holiday_years'] = []
    for year in [this_year, this_year+1]:
        data['holiday_years'].append(
            {'year': year,
             'holidays': Holiday.get_holidays_for_year(year=year, kwargs={'paid_holiday': True})}
        )
    data['today'] = datetime.date.today()
    return render(request, 'timepiece/pto/home.html', data)


@cbv_decorator(permission_required('crm.add_paidtimeoffrequest'))
class CreatePTORequest(CreateView):
    model = PaidTimeOffRequest
    form_class = CreateEditPTORequestForm
    template_name = 'timepiece/pto/create_edit.html'

    def form_valid(self, form):
        user_profile = UserProfile.objects.get(user=self.request.user)
        form.instance.user_profile = user_profile
        instance = form.save()
        emails.new_pto(instance, reverse('pto_request_details', args=(instance.id,)))
        return super(CreatePTORequest, self).form_valid(form)


@cbv_decorator(permission_required('crm.change_paidtimeoffrequest'))
class EditPTORequest(UpdateView):
    model = PaidTimeOffRequest
    form_class = CreateEditPTORequestForm
    template_name = 'timepiece/pto/create_edit.html'
    pk_url_kwarg = 'pto_request_id'

    def form_valid(self, form):
        form.instance.approver = None
        form.instance.approval_date = None
        return super(EditPTORequest, self).form_valid(form)


@cbv_decorator(permission_required('crm.delete_paidtimeoffrequest'))
class DeletePTORequest(DeleteView):
    model = PaidTimeOffRequest
    success_url = reverse_lazy('pto')
    pk_url_kwarg = 'pto_request_id'
    template_name = 'timepiece/delete_object.html'


@cbv_decorator(permission_required('crm.can_approve_pto_requests'))
class ApprovePTORequest(UpdateView):
    model = PaidTimeOffRequest
    form_class = ApproveDenyPTORequestForm
    pk_url_kwarg = 'pto_request_id'
    template_name = 'timepiece/pto/approve.html'

    def form_valid(self, form):
        form.instance.approver = self.request.user
        form.instance.approval_date = datetime.datetime.now()
        form.instance.status = PaidTimeOffRequest.APPROVED
        up = form.instance.user_profile

        # add PTO log enntries
        # add timesheet entries
        delta = form.instance.pto_end_date - form.instance.pto_start_date
        days_delta = delta.days + 1
        for i in range(days_delta):
            date = form.instance.pto_start_date + datetime.timedelta(days=i)
            start_time = datetime.datetime.combine(date, datetime.time(8))
            hours = float(form.instance.amount)/float(days_delta)
            end_time = start_time + datetime.timedelta(hours=hours)
            
            # add pto log entry
            pto_log = PaidTimeOffLog(user_profile=up, 
                                     date=date,
                                     amount=-1*(float(form.instance.amount) / float(days_delta)), 
                                     comment=form.instance.comment,
                                     pto_request=form.instance)
            pto_log.save()

            # add timesheet entry
            entry = Entry(user=form.instance.user_profile.user,
                          project=Project.objects.get(id=utils.get_setting('TIMEPIECE_PTO_PROJECT')[date.year]),
                          activity=Activity.objects.get(code='PTO', name='Paid Time Off'),
                          location=Location.objects.get(id=3),
                          start_time=start_time,
                          end_time=end_time,
                          comments='Approved PTO %s.' % form.instance.pk,
                          hours=hours,
                          pto_log=pto_log,
                          mechanism=Entry.PTO)
            entry.save()

        return super(ApprovePTORequest, self).form_valid(form)


@cbv_decorator(permission_required('crm.can_approve_pto_requests'))
class DenyPTORequest(UpdateView):
    model = PaidTimeOffRequest
    form_class = ApproveDenyPTORequestForm
    pk_url_kwarg = 'pto_request_id'
    template_name = 'timepiece/pto/deny.html'

    def form_valid(self, form):
        form.instance.approver = self.request.user
        form.instance.approval_date = datetime.datetime.now()
        form.instance.status = PaidTimeOffRequest.DENIED
        return super(DenyPTORequest, self).form_valid(form)

@login_required
def pto_request_details(request, pto_request_id):
    try:
        data = {'pto_request': PaidTimeOffRequest.objects.get(id=int(pto_request_id))}
        return render(request, 'timepiece/pto/details.html', data)
    except:
        return render(request, 'timepiece/pto/details.html', {})

## MILESTONES
@cbv_decorator(permission_required('crm.add_milestone'))
class ViewMilestone(DetailView):
    model = Milestone
    pk_url_kwarg = 'milestone_id'
    template_name = 'timepiece/project/milestone/view.html'

@cbv_decorator(permission_required('crm.add_milestone'))
class CreateMilestone(CreateView):
    model = Milestone
    form_class = CreateEditMilestoneForm
    template_name = 'timepiece/project/milestone/create_edit.html'

    def form_valid(self, form):
        form.instance.project = Project.objects.get(id=int(self.kwargs['project_id']))
        return super(CreateMilestone, self).form_valid(form)

    def get_success_url(self):
        return '/timepiece/project/%d' % int(self.kwargs['project_id'])


@cbv_decorator(permission_required('crm.change_milestone'))
class EditMilestone(UpdateView):
    model = Milestone
    form_class = CreateEditMilestoneForm
    template_name = 'timepiece/project/milestone/create_edit.html'
    pk_url_kwarg = 'milestone_id'

    def get_success_url(self):
        return '/timepiece/project/%d' % int(self.kwargs['project_id'])


@cbv_decorator(permission_required('crm.delete_milestone'))
class DeleteMilestone(DeleteView):
    model = Milestone
    pk_url_kwarg = 'milestone_id'
    template_name = 'timepiece/delete_object.html'

    def get_success_url(self):
        return '/timepiece/project/%d' % int(self.kwargs['project_id'])


## ACTIVITY GOALS
@cbv_decorator(permission_required('crm.add_activitygoal'))
class CreateActivityGoal(CreateView):
    model = ActivityGoal
    form_class = CreateEditActivityGoalForm
    template_name = 'timepiece/project/milestone/activity_goal/create_edit.html'

    def form_valid(self, form):
        form.instance.milestone = Milestone.objects.get(id=int(self.kwargs['milestone_id']))
        return super(CreateActivityGoal, self).form_valid(form)

    def get_success_url(self):
        return '/timepiece/project/%d/milestone/%d' % (int(self.kwargs['project_id']), int(self.kwargs['milestone_id']))


@cbv_decorator(permission_required('crm.change_activitygoal'))
class EditActivityGoal(UpdateView):
    model = ActivityGoal
    form_class = CreateEditActivityGoalForm
    template_name = 'timepiece/project/milestone/activity_goal/create_edit.html'
    pk_url_kwarg = 'activity_goal_id'

    def get_success_url(self):
        return '/timepiece/project/%d/milestone/%d' % (int(self.kwargs['project_id']), int(self.kwargs['milestone_id']))


@cbv_decorator(permission_required('crm.delete_activitygoal'))
class DeleteActivityGoal(DeleteView):
    model = ActivityGoal
    pk_url_kwarg = 'activity_goal_id'
    template_name = 'timepiece/delete_object.html'

    def get_success_url(self):
        return '/timepiece/project/%d/milestone/%d' % (int(self.kwargs['project_id']), int(self.kwargs['milestone_id']))
