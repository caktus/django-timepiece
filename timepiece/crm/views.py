import datetime
from dateutil.relativedelta import relativedelta
import urllib
import json
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse, reverse_lazy
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import (CreateView, DeleteView, DetailView,
        UpdateView, FormView, View)
from django.forms import widgets

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
        CreateEditActivityGoalForm, ApproveDenyPTORequestForm,
        CreateEditPaidTimeOffLog, AddBusinessNoteForm, 
        CreateEditBusinessDepartmentForm, CreateEditContactForm, 
        AddContactNoteForm)
from timepiece.crm.models import (Business, Project, ProjectRelationship, UserProfile,
    PaidTimeOffLog, PaidTimeOffRequest, Milestone, ActivityGoal, BusinessNote,
    BusinessDepartment, Contact, ContactNote)
from timepiece.crm.utils import grouped_totals, project_activity_goals_with_progress
from timepiece.entries.models import Entry, Activity, Location
from timepiece.reports.forms import HourlyReportForm

from holidays.models import Holiday
from . import emails

import workdays


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
    form = YearMonthForm({'year':int(year), 'month':int(month), 'half':half})
    user = User.objects.get(pk=user_id)
    if form.is_valid():
        from_date, to_date = form.save()
        entries = Entry.no_join.filter(status=Entry.VERIFIED, user=user,
            start_time__gte=from_date, end_time__lte=to_date, writedown=False)
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
    entries_qs = Entry.objects.filter(user=user, writedown=False)
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
    summary = Entry.summary(user, from_date, to_date, writedown=False)

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
                                   end_time__lt=to_date,
                                   writedown=False)
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
        #year_month_form = YearMonthForm(self.request.GET or None)
        filter_form = HourlyReportForm(self.request.GET or None)
        
        if self.request.GET and filter_form.is_valid():
            from_date, to_date = filter_form.save()
            incl_billable = filter_form.cleaned_data['billable']
            incl_non_billable = filter_form.cleaned_data['non_billable']
        else:
            # date = utils.add_timezone(datetime.datetime.today())
            # from_date = utils.get_month_start(date).date()
            from_date, to_date = utils.get_bimonthly_dates(datetime.date.today())
            to_date = from_date + relativedelta(months=1)
            incl_billable = True
            incl_non_billable = True
        
        from_datetime = datetime.datetime.combine(from_date, 
            datetime.datetime.min.time())
        to_datetime = datetime.datetime.combine(to_date,
            datetime.datetime.max.time())

        entries_qs = Entry.objects.filter(start_time__gte=from_datetime,
                                          end_time__lt=to_datetime,
                                          project=project)
        if incl_billable and not incl_non_billable:
            entries_qs = entries_qs.filter(activity__billable=True)
        elif not incl_billable and incl_non_billable:
            entries_qs = entries_qs.filter(activity__billable=False)
        elif incl_billable and incl_non_billable:
            pass
        else:
            entries_qs = entries_qs.filter(activity__billable=False).filter(activity__billable=True) # should return nothing
        # entries_qs = entries_qs.timespan(from_date, span='month').filter(
        #     project=project
        # )
        extra_values = ('start_time', 'end_time', 'comments', 'seconds_paused',
                'id', 'location__name', 'project__name', 'activity__name',
                'status', 'writedown')
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
            #'year_month_form': year_month_form,
            'filter_form': self.get_form(),
            'from_date': from_date,
            'to_date': to_date - relativedelta(days=1),
            'entries': month_entries,
            'total': total,
            'user_entries': user_entries,
            'activity_entries': activity_entries,
        })
        return context

    @property
    def defaults(self):
        """Default filter form data when no GET data is provided."""
        # Set default date span to current pay period
        start, end = utils.get_bimonthly_dates(datetime.date.today())
        end -= relativedelta(days=1)
        return {
            'from_date': start,
            'to_date': end,
            'billable': True,
            'non_billable': True,
            'paid_time_off': False,
            'trunc': 'day',
            'projects': [],
        }

    def get_form(self):
        data = self.request.GET or self.defaults
        data = data.copy()  # make mutable
        # Fix booleans - the strings "0" and "false" are True in Python
        for key in ['billable', 'non_billable', 'paid_time_off']:
            data[key] = key in data and \
                        str(data[key]).lower() in ('on', 'true', '1')

        form = HourlyReportForm(data)
        for field in ['projects', 'paid_time_off', 'trunc']:
            form.fields[field].widget = widgets.HiddenInput()
        return form


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
            'Writedown',
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
                entry['writedown'],
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

@permission_required('crm.view_business')
def business(request):
    data = [{'short_name':b.short_name, 'name':b.name} for b in Business.objects.all().order_by('short_name')]
    return HttpResponse(json.dumps(data), content_type="application/json")

@cbv_decorator(permission_required('crm.view_business'))
class ViewBusiness(DetailView):
    model = Business
    pk_url_kwarg = 'business_id'
    template_name = 'timepiece/business/view.html'

    def get_context_data(self, **kwargs):
        context = super(ViewBusiness, self).get_context_data(**kwargs)
        context['add_business_note_form'] = AddBusinessNoteForm()
        # context['ticket_history'] = GeneralTaskHistory.objects.filter(
        #     general_task=self.object).order_by('-last_activity')
        # context['is_it_admin'] = bool(len(self.request.user.groups.filter(id=8)))
        # context['is_aac_mgmt'] = bool(len(self.request.user.groups.filter(id=5)))
        # context['add_user_form'] = SelectUserForm()
        return context

@cbv_decorator(permission_required('crm.view_business'))
class ViewBusinessDepartment(DetailView):
    model = BusinessDepartment
    pk_url_kwarg = 'business_department_id'
    template_name = 'timepiece/business/department/view.html'

    def get_context_data(self, **kwargs):
        context = super(ViewBusinessDepartment, self).get_context_data(**kwargs)
        # context['add_business_note_form'] = AddBusinessNoteForm()
        # context['ticket_history'] = GeneralTaskHistory.objects.filter(
        #     general_task=self.object).order_by('-last_activity')
        # context['is_it_admin'] = bool(len(self.request.user.groups.filter(id=8)))
        # context['is_aac_mgmt'] = bool(len(self.request.user.groups.filter(id=5)))
        # context['add_user_form'] = SelectUserForm()
        return context

@cbv_decorator(permission_required('workflow.add_businessnote'))
class AddBusinessNote(View):

    def post(self, request, *args, **kwargs):
        user = self.request.user
        business = Business.objects.get(id=int(kwargs['business_id']))
        note = BusinessNote(business=business,
                            author=user,
                            text=request.POST.get('text', ''))
        if len(note.text):
            note.save()
        return HttpResponseRedirect(request.GET.get('next', None) or reverse('view_business', args=(business.id,)))



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

@cbv_decorator(permission_required('crm.add_businessdepartment'))
class CreateBusinessDepartment(CreateView):
    model = BusinessDepartment
    form_class = CreateEditBusinessDepartmentForm
    template_name = 'timepiece/business/department/create_edit.html'

    def get_context_data(self, **kwargs):
        kwargs.update({'business': Business.objects.get(id=int(self.kwargs['business_id']))})
        return super(CreateBusinessDepartment, self).get_context_data(**kwargs)

    def get_form(self, *args, **kwargs):
        form = super(CreateBusinessDepartment, self).get_form(*args, **kwargs)
        form.fields['business'].widget = widgets.HiddenInput()
        form.fields['business'].initial = Business.objects.get(id=int(self.kwargs['business_id']))
        return form

    def form_valid(self, form):
        form.instance.business = Business.objects.get(id=int(self.kwargs['business_id']))
        return super(CreateBusinessDepartment, self).form_valid(form)

    def get_success_url(self):
        # messages.info(self.request, 'Your settings have been updated.')
        return reverse('view_business', args=(int(self.kwargs['business_id']), ))

@cbv_decorator(permission_required('crm.change_businessdepartment'))
class EditBusinessDepartment(UpdateView):
    model = BusinessDepartment
    form_class = CreateEditBusinessDepartmentForm
    template_name = 'timepiece/business/department/create_edit.html'
    pk_url_kwarg = 'business_department_id'

    def get_context_data(self, **kwargs):
        kwargs.update({'business': Business.objects.get(id=int(self.kwargs['business_id']))})
        return super(EditBusinessDepartment, self).get_context_data(**kwargs)

    def get_form(self, *args, **kwargs):
        form = super(EditBusinessDepartment, self).get_form(*args, **kwargs)
        form.fields['business'].widget = widgets.HiddenInput()
        form.fields['business'].initial = Business.objects.get(id=int(self.kwargs['business_id']))
        return form

    def form_valid(self, form):
        form.instance.business = Business.objects.get(id=int(self.kwargs['business_id']))
        return super(EditBusinessDepartment, self).form_valid(form)

    def get_success_url(self):
        # messages.info(self.request, 'Your settings have been updated.')
        return reverse('view_business', args=(int(self.kwargs['business_id']), ))


@cbv_decorator(permission_required('crm.delete_businessdepartment'))
class DeleteBusinessDepartment(DeleteView):
    model = BusinessDepartment
    pk_url_kwarg = 'business_department_id'
    template_name = 'timepiece/delete_object.html'

    def get_success_url(self):
        if self.object:
            return reverse('view_business', args=(self.object.business,))
        else:
            return reverse('list_businesses')

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
        return super(ListUsers, self).get_queryset().select_related().order_by('last_name', 'first_name')


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
class ListProjects(SearchListView, CSVViewMixin):
    model = Project
    form_class = ProjectSearchForm
    redirect_if_one_result = True
    search_fields = ['name__icontains', 'description__icontains', 'code__icontains',
    'point_person__first_name__icontains', 'point_person__last_name__icontains']
    template_name = 'timepiece/project/list.html'

    def get(self, request, *args, **kwargs):
        self.export_project_list = request.GET.get('export_project_list', False)
        if self.export_project_list:
            kls = CSVViewMixin

            form_class = self.get_form_class()
            self.form = self.get_form(form_class)
            self.object_list = self.get_queryset()
            self.object_list = self.filter_results(self.form, self.object_list)

            allow_empty = self.get_allow_empty()
            if not allow_empty and len(self.object_list) == 0:
                raise Http404("No results found.")

            context = self.get_context_data(form=self.form,
                object_list=self.object_list)


            # qs = self.get_queryset()
            # self.object_list = qs
            # self.get_context_object_name(qs)
            # kwargs['object_list'] = qs
            # print 'count', qs.count()
            # context = self.get_context_data(**kwargs)
            return kls.render_to_response(self, context)
        else:
            return super(ListProjects, self).get(request, *args, **kwargs)
    
    def filter_form_valid(self, form, queryset):
        print 'form', form, 'queryset', queryset
        queryset = super(ListProjects, self).filter_form_valid(form, queryset)
        status = form.cleaned_data['status']
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_filename(self, context):
        request = self.request.GET.copy()
        status = request.get('status')
        search = request.get('search', '(empty)')
        return 'project_search_{0}_{1}.csv'.format(status, search)

    def convert_context_to_csv(self, context):
        """Convert the context dictionary into a CSV file."""
        content = []
        project_list = context['project_list']
        if self.export_project_list:
            # this is a special csv export, different than stock Timepiece,
            # requested by AAC Engineering for their detailed reporting reqs
            headers = ['Project Code', 'Project Name', 'Type', 'Business', 'Status',
                       'Billable', 'Finder', 'Minder', 'Binder', 'Description',
                       'Contracts -->']
            content.append(headers)
            for project in project_list:
                row = [project.code, project.name, str(project.type),
                       '%s:%s'%(project.business.short_name, project.business.name),
                       project.status, project.billable, str(project.finder),
                       str(project.point_person), str(project.binder), 
                       project.description]
                for contract in project.contracts.all():
                    row.append(str(contract))
                content.append(row)
        return content


@cbv_decorator(permission_required('crm.view_project'))
class ViewProject(DetailView):
    model = Project
    pk_url_kwarg = 'project_id'
    template_name = 'timepiece/project/view.html'

    def get_context_data(self, **kwargs):
        kwargs.update({'add_user_form': SelectUserForm(),
                       'activity_goals': project_activity_goals_with_progress(self.object)})
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
    if request.user.has_perm('crm.can_approve_pto_requests') or request.user.has_perm('crm.can_process_pto_requests'):
        data['pto_approvals'] = PaidTimeOffRequest.objects.filter(Q(status=PaidTimeOffRequest.PENDING) | Q(status=PaidTimeOffRequest.APPROVED))
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

    def get_form(self, *args, **kwargs):
        form = super(CreatePTORequest, self).get_form(*args, **kwargs)
        if not self.request.user.profile.earns_pto:
            form.fields['pto'].widget.attrs['disabled'] = 'disabled'
            form.fields['pto'].initial = False
        return form

    def form_valid(self, form):
        user_profile = UserProfile.objects.get(user=self.request.user)
        form.instance.user_profile = user_profile
        if not user_profile.earns_pto:
            form.instance.pto = False
        instance = form.save()
        emails.new_pto(instance,
                       reverse('pto_request_details', args=(instance.id,)),
                       reverse('approve_pto_request', args=(instance.id,)),
                       reverse('deny_pto_request', args=(instance.id,)),
                      )
        return super(CreatePTORequest, self).form_valid(form)


@cbv_decorator(permission_required('crm.change_paidtimeoffrequest'))
class EditPTORequest(UpdateView):
    model = PaidTimeOffRequest
    form_class = CreateEditPTORequestForm
    template_name = 'timepiece/pto/create_edit.html'
    pk_url_kwarg = 'pto_request_id'

    def get_form(self, *args, **kwargs):
        form = super(EditPTORequest, self).get_form(*args, **kwargs)
        if not self.request.user.profile.earns_pto:
            form.fields['pto'].widget.attrs['disabled'] = 'disabled'
            form.fields['pto'].initial = False
        return form

    def form_valid(self, form):
        form.instance.approver = None
        form.instance.approval_date = None
        if not form.instance.user_profile.earns_pto:
            form.instance.pto = False
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

        # get holidays in years covered by PTO to make sure that they are not
        # included as days to use PTO hours
        holidays = []
        for year in range(form.instance.pto_start_date.year, form.instance.pto_end_date.year+1):
            holiday_dates = [h['date'] for h in Holiday.get_holidays_for_year(year, {'paid_holiday':True})]
            holidays.extend(holiday_dates)
        # get number of workdays found in between the start and stop dates
        num_workdays = workdays.networkdays(form.instance.pto_start_date,
                                            form.instance.pto_end_date,
                                            holidays)
        
        # add PTO log entries
        if form.instance.pto:
            delta = form.instance.pto_end_date - form.instance.pto_start_date
            hours = float(form.instance.amount)/float(num_workdays)
            days_delta = delta.days + 1
            for i in range(days_delta):
                date = form.instance.pto_start_date + datetime.timedelta(days=i)
                
                # if the date is weekend or holiday, skip it
                if (date.weekday() >= 5) or (date in holidays):
                    continue

                start_time = datetime.datetime.combine(date, datetime.time(8))
                end_time = start_time + datetime.timedelta(hours=hours)
                
                # add pto log entry
                pto_log = PaidTimeOffLog(user_profile=up, 
                                         date=date,
                                         amount=-1*(float(form.instance.amount) / float(num_workdays)), 
                                         comment=form.instance.comment,
                                         pto_request=form.instance)
                pto_log.save()

                # if pto entry, add timesheet entry
                if form.instance.pto and form.instance.amount > 0:
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


@cbv_decorator(permission_required('crm.can_process_pto_requests'))
class ProcessPTORequest(UpdateView):
    model = PaidTimeOffRequest
    form_class = ApproveDenyPTORequestForm
    pk_url_kwarg = 'pto_request_id'
    template_name = 'timepiece/pto/process.html'

    def form_valid(self, form):
        form.instance.processor = self.request.user
        form.instance.process_date = datetime.datetime.now()
        form.instance.status = PaidTimeOffRequest.PROCESSED
        return super(ProcessPTORequest, self).form_valid(form)

@cbv_decorator(permission_required('crm.add_paidtimeofflog'))
class CreatePTOLogEntry(CreateView):
    model = PaidTimeOffLog
    form_class = CreateEditPaidTimeOffLog
    template_name = 'timepiece/pto/create-edit-log.html'

    def get_success_url(self):
        return '/timepiece/pto/all_history/'

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

    def get_form(self, *args, **kwargs):
        form = super(CreateActivityGoal, self).get_form(*args, **kwargs)
        project = Project.objects.get(id=int(self.kwargs['project_id']))
        if project.activity_group:
            activities = [(a.id, a.name) for a in project.activity_group.activities.all()]
            activities.insert(0, ('', '---------'))
            form.fields['activity'].choices = activities
        return form

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

    def get_form(self, *args, **kwargs):
        form = super(EditActivityGoal, self).get_form(*args, **kwargs)
        project = Project.objects.get(id=int(self.kwargs['project_id']))
        if project.activity_group is not None:
            activities = [(a.id, a.name) for a in project.activity_group.activities.all()]
            activities.insert(0, ('', '---------'))
            form.fields['activity'].choices = activities
        return form

    def get_success_url(self):
        return '/timepiece/project/%d/milestone/%d' % (int(self.kwargs['project_id']), int(self.kwargs['milestone_id']))


@cbv_decorator(permission_required('crm.delete_activitygoal'))
class DeleteActivityGoal(DeleteView):
    model = ActivityGoal
    pk_url_kwarg = 'activity_goal_id'
    template_name = 'timepiece/delete_object.html'

    def get_success_url(self):
        return '/timepiece/project/%d/milestone/%d' % (int(self.kwargs['project_id']), int(self.kwargs['milestone_id']))

from itertools import groupby
import numpy
import sys
import traceback
import pprint
pp = pprint.PrettyPrinter(indent=4)
PROJECT_MANAGEMENT_ACTIVITY_ID = 12
PROJECT_DEVELOPMENT_ACTIVITY_ID = 11
TECH_WRITING_ACTIVITY_ID = 17
@login_required
def burnup_chart_data(request, project_id):
    # try:
    #     data = settings.MONGO_CLIENT.timepiece.burnup_chart.find_one(
    #         {'project': project.id,
    #          'date': str(datetime.date.today())})
    #     if data:
    #         return HttpResponse(json.dumps(data), status=200, mimetype='application/json')
    # except:
    #     pass
    try:
        project = Project.objects.get(id=int(project_id))
        try:
            start_date = Entry.objects.filter(project=project).order_by('start_time')[0].start_time.date()
        except:
            start_date = datetime.date.today() - datetime.timedelta(days=7)
        try:
            end_date = max(Entry.objects.filter(project=project).order_by('-start_time')[0].start_time.date(),
                           Milestone.objects.filter(project=project).order_by('-due_date')[0].due_date,
                           datetime.date.today() + datetime.timedelta(days=7))
        except:
            try:
                end_date = max(Entry.objects.filter(project=project).order_by('-start_time')[0].start_time.date(),
                               datetime.date.today() + datetime.timedelta(days=7))
            except:
                end_date = datetime.date.today() + datetime.timedelta(days=7)
        end_date += datetime.timedelta(days=1)
        mgmt_entries_raw = Entry.objects.filter(project=project).values('start_time', 'activity', 'hours').order_by('start_time')
        mgmt_entries = []
        for me in mgmt_entries_raw:
            mgmt_entries.append({'hours': float(me['hours']), 'activity': me['activity'], 'date': me['start_time'].date()})
        entries = {}
        for date, date_entries in groupby(mgmt_entries, lambda x: x['date']):
            if isinstance(date, datetime.datetime):
                date = date.date()
            current_entries = {'project_management': 0,
                               'project_development': 0,
                               'tech_writing': 0,
                               'other': 0}
            for de in list(date_entries):
                if de['activity'] == PROJECT_MANAGEMENT_ACTIVITY_ID:
                    current_entries['project_management'] += de['hours']
                elif de['activity'] == PROJECT_DEVELOPMENT_ACTIVITY_ID:
                    current_entries['project_development'] += de['hours']
                elif de['activity'] == TECH_WRITING_ACTIVITY_ID:
                    current_entries['tech_writing'] += de['hours']
                else:
                    current_entries['other'] += de['hours']
            entries[str(date)] = current_entries

        if start_date.day < 15:
            start_date = datetime.date(start_date.year, start_date.month, 1)
        else:
            start_date = datetime.date(start_date.year, start_date.month, 15)
        current_date = start_date
        project_management = []
        project_development = []
        tech_writing = []
        other = []
        plot_dates = []
        for i in range((end_date - start_date).days):
            if str(current_date) in entries.keys():
                project_management.append(entries[str(current_date)]['project_management'])
                project_development.append(entries[str(current_date)]['project_development'])
                tech_writing.append(entries[str(current_date)]['tech_writing'])
                other.append(entries[str(current_date)]['other'])
            else:
                project_management.append(0)
                project_development.append(0)
                tech_writing.append(0)
                other.append(0)
            plot_dates.append(str(current_date))
            current_date += datetime.timedelta(days=1)
        plot_dates.insert(0, 'plot_dates')
        project_management = numpy.cumsum(project_management).tolist()
        project_management.insert(0, 'proj_mgmt_actual')
        project_development = numpy.cumsum(project_development).tolist()
        project_development.insert(0, 'proj_dev_actual')
        tech_writing = numpy.cumsum(tech_writing).tolist()
        tech_writing.insert(0, 'tech_writing_actual')
        other = numpy.cumsum(other).tolist()
        other.insert(0, 'other_actual')

        # get milestones and activity goals
        milestones = [{'value': str(datetime.date.today()), 'class':'today', 'text':'TODAY'}]
        activity_goals = [['proj_mgmt_target'],
                          ['proj_dev_target'],
                          ['tech_writing_target'],
                          ['other_target']]
        for ms in Milestone.objects.filter(project=project).order_by('due_date'):
            milestones.append({'value': str(ms.due_date), 'text': ms.name})
            # for ag in ms.activity_goals:
            #     gh = float(ag.goal_hours)
            #     if ag.activity is None:
            #         for i in range((ms.due_date - start_date).days + 1):
            #             activity_goals[3].append(gh)
            #     elif ag.activity.id == PROJECT_MANAGEMENT_ACTIVITY_ID:
            #         for i in range((ms.due_date - start_date).days + 1):
            #             activity_goals[0].append(gh)
            #     elif ag.activity.id == PROJECT_DEVELOPMENT_ACTIVITY_ID:
            #         for i in range((ms.due_date - start_date).days + 1):
            #             activity_goals[1].append(gh)
            #     elif ag.activity.id == TECH_WRITING_ACTIVITY_ID:
            #         for i in range((ms.due_date - start_date).days + 1):
            #             activity_goals[2].append(gh)
        
        # get ActivityGoals and group by Activity
        ag_temp = [[], [], [], []]
        for ag in ActivityGoal.objects.filter(milestone__project=project):
            if ag.activity is None:
                ag_temp[3].append(ag)
            elif ag.activity.id == PROJECT_MANAGEMENT_ACTIVITY_ID:
                ag_temp[0].append(ag)
            elif ag.activity.id == PROJECT_DEVELOPMENT_ACTIVITY_ID:
                ag_temp[1].append(ag)
            elif ag.activity.id == TECH_WRITING_ACTIVITY_ID:
                ag_temp[2].append(ag)
            else:
                ag_temp[3].append(ag)

        # sort ActivityGoals by date within categories
        for i in range(len(ag_temp)):
            ag_temp[i] = sorted(ag_temp[i], key=lambda x: x.date or datetime.date.today())
        
        for i in range(len(ag_temp)):
            if len(ag_temp[i]) == 0:
                continue
            ag_hours = []
            for employee, ags in groupby(ag_temp[i], lambda x: x.employee):
                last_date = start_date
                vals = []
                for ag in ags:
                    gh = float(ag.goal_hours)
                    for j in range((ag.milestone.due_date - last_date).days + 1):
                        vals.append(gh)
                    last_date = ag.milestone.due_date
                ag_hours.append(vals)
            
            max_len = len(ag_hours[0])
            for ag_hours_employee in ag_hours:
                max_len = max(max_len, len(ag_hours_employee))
            for ag_hours_employee in ag_hours:
                val = ag_hours_employee[-1]
                while len(ag_hours_employee) < max_len:
                    ag_hours_employee.append(val)
            activity_goals[i].extend(list(numpy.sum(ag_hours, axis=0)))

        data = {'entries': entries,
                'start_date': str(start_date),
                'end_date': str(end_date),
                'plot_dates': plot_dates,
                'project_management': project_management,
                'project_development': project_development,
                'tech_writing': tech_writing,
                'other': other,
                'milestones': milestones,
                'activity_goals': activity_goals}
        try:
            # settings.MONGO_CLIENT.timepiece.burnup_chart.save(
            #     {'project': project.id,
            #      'date': str(datetime.date.today()),
            #      'data': data})
            f = open(os.path.join(settings.BURNUP_CACHE, '%s-%d.json'%(str(datetime.date.today()), project.id)), 'w')
            f.write('var data = ' + json.dumps(data) + ';')
            f.close()
        except:
            print sys.exc_info(), traceback.format_exc()
            pass
        return HttpResponse(json.dumps(data), status=200, mimetype='application/json')
    except:
        print sys.exc_info(), traceback.format_exc()
        return HttpResponse(json.dumps({}), status=200, mimetype='application/json')

@login_required
def burnup_chart(request, project_id):
    context = {'project': Project.objects.get(id=int(project_id))}
    return render(request, 'timepiece/project/burnup_charts/burnup_chart.html', context)
    # render_to_pdf(request, 'project-test')

@cbv_decorator(permission_required('crm.view_contact'))
class ListContacts(SearchListView, CSVViewMixin):
    model = Contact
    redirect_if_one_result = True
    search_fields = ['first_name__icontains', 'last_name__icontains',
                     'email__icontains', 'business__name__icontains', 
                     'business_department__name__icontains']
    template_name = 'timepiece/contact/list.html'

    def get(self, request, *args, **kwargs):
        self.export_contact_list = request.GET.get('export_contact_list', False)
        if self.export_contact_list:
            kls = CSVViewMixin

            form_class = self.get_form_class()
            self.form = self.get_form(form_class)
            self.object_list = self.get_queryset()
            self.object_list = self.filter_results(self.form, self.object_list)

            allow_empty = self.get_allow_empty()
            if not allow_empty and len(self.object_list) == 0:
                raise Http404("No results found.")

            context = self.get_context_data(form=self.form,
                object_list=self.object_list)

            return kls.render_to_response(self, context)
        else:
            return super(ListContacts, self).get(request, *args, **kwargs)
    
    # def filter_form_valid(self, form, queryset):
    #     queryset = super(ListContacts, self).filter_form_valid(form, queryset)
    #     status = form.cleaned_data['status']
    #     if status:
    #         queryset = queryset.filter(status=status)
    #     return queryset

    def get_filename(self, context):
        request = self.request.GET.copy()
        search = request.get('search', '(empty)')
        return 'contact_search_{0}.csv'.format(search)

    def convert_context_to_csv(self, context):
        """Convert the context dictionary into a CSV file."""
        content = []
        contact_list = context['contact_list']
        if self.export_contact_list:
            # this is a special csv export, different than stock Timepiece,
            # requested by AAC Engineering for their detailed reporting reqs
            headers = ['Salutaton', 'First Name', 'Last Name', 'Title', 'Email',
                       'Office Phone', 'Mobile Phone', 'Home Phone', 
                       'Other Phone', 'Fax', 'Business Name',
                       'Business Department Name', 'Assistant Name',
                       'Assistant Phone', 'Assistant Email', 'Mailing Street',
                       'Mailing City', 'Mailing State', 'Mailing Postal Code',
                       'Mailing Mailstop', 'Mailing Country', 'Mailing Latitude',
                       'Mailing Longitude', 'Other Street', 'Other City', 
                       'Other State', 'Other Postal Code', 'Other Mailstop', 
                       'Other Country', 'Other Latitude', 'Other Longitude', 
                       'Opted Out of Email', 'Opted Out of Fax', 'DO NOT CALL',
                       'Birthday', 'Lead Source Email', 'Tags -->']
            content.append(headers)
            for contact in contact_list:
                row = [contact.salutation, contact.first_name, contact.last_name, 
                       contact.title, contact.email, contact.office_phone,
                       contact.mobile_phone, contact.home_phone,
                       contact.other_phone, contact.fax, contact.business,
                       contact.business_department, contact.assistant_name,
                       contact.assistant_phone, contact.assistant_email,
                       contact.mailing_street, contact.mailing_city,
                       contact.mailing_state, contact.mailing_postalcode,
                       contact.mailing_mailstop, contact.mailing_country,
                       contact.mailing_lat, contact.mailing_lon, contact.other_street,
                       contact.other_city, contact.other_state,
                       contact.other_postalcode, contact.other_mailstop,
                       contact.other_country, contact.other_lat, contact.other_lon,
                       contact.has_opted_out_of_email, contact.has_opted_out_of_fax,
                       contact.do_not_call, contact.birthday, contact.lead_source.email]
                for tag in contact.tags.all():
                    row.append(tag)

                content.append(row)
        return content

@cbv_decorator(permission_required('crm.view_contact'))
class ViewContact(DetailView):
    model = Contact
    pk_url_kwarg = 'contact_id'
    template_name = 'timepiece/contact/view.html'

    def get_context_data(self, **kwargs):
        context = super(ViewContact, self).get_context_data(**kwargs)
        context['add_contact_note_form'] = AddContactNoteForm()
        return context

@cbv_decorator(permission_required('workflow.add_contactnote'))
class AddContactNote(View):

    def post(self, request, *args, **kwargs):
        user = self.request.user
        contact = Contact.objects.get(id=int(kwargs['contact_id']))
        note = ContactNote(contact=contact,
                           author=user,
                           text=request.POST.get('text', ''))
        if len(note.text):
            note.save()
        return HttpResponseRedirect(request.GET.get('next', None) or reverse('view_contact', args=(contact.id,)))

@cbv_decorator(permission_required('workflow.add_contactnote'))
class ContactTags(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=200)

    def post(self, request, *args, **kwargs):
        contact = Contact.objects.get(id=int(kwargs['contact_id']))
        tag = request.POST.get('tag')
        for t in tag.split(','):
            if len(t):
                contact.tags.add(t)
        tags = [t.name for t in contact.tags.all()]
        return HttpResponse(json.dumps({'tags': tags}),
                            content_type="application/json",
                            status=200)

@cbv_decorator(permission_required('workflow.delete_contact'))
class RemoveContactTag(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=501)

    def post(self, request, *args, **kwargs):
        if request.user.is_superuser or bool(len(request.user.groups.filter(id=8))):
            contact = Contact.objects.get(id=int(kwargs['contact_id']))
            tag = request.POST.get('tag')
            if len(tag):
                contact.tags.remove(tag)
        tags = [t.name for t in contact.tags.all()]
        return HttpResponse(json.dumps({'tags': tags}),
                            content_type="application/json",
                            status=200)


@cbv_decorator(permission_required('crm.add_contact'))
class CreateContact(CreateView):
    model = Contact
    form_class = CreateEditContactForm
    template_name = 'timepiece/contact/create_edit.html'


@cbv_decorator(permission_required('crm.delete_contact'))
class DeleteContact(DeleteView):
    model = Contact
    success_url = reverse_lazy('list_contacts')
    pk_url_kwarg = 'contact_id'
    template_name = 'timepiece/delete_object.html'


@cbv_decorator(permission_required('crm.change_contact'))
class EditContact(UpdateView):
    model = Contact
    form_class = CreateEditContactForm
    template_name = 'timepiece/contact/create_edit.html'
    pk_url_kwarg = 'contact_id'