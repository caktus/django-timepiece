import datetime
from dateutil.relativedelta import relativedelta
import urllib
import json
import os

from six.moves.urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse, reverse_lazy
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import (CreateView, DeleteView, DetailView,
        UpdateView, FormView, View, TemplateView)
from django.forms import widgets

from timepiece import utils
from timepiece.utils import get_setting
from timepiece.forms import (YearMonthForm, UserYearMonthForm, DateForm,
    UserDateForm, StatusUserDateForm, StatusDateForm)
from timepiece.templatetags.timepiece_tags import seconds_to_hours
from timepiece.utils.csv import CSVViewMixin
from timepiece.utils.search import SearchListView
from timepiece.utils.views import cbv_decorator

from timepiece.crm.forms import (CreateEditBusinessForm, CreateProjectForm, EditProjectForm,
        EditUserSettingsForm, EditProjectRelationshipForm, SelectProjectForm,
        EditUserForm, CreateUserForm, SelectUserForm, ProjectSearchForm,
        BusinessSearchForm, QuickSearchForm, CreateEditPTORequestForm, CreateEditMilestoneForm,
        ApproveMilestoneForm, AddMilestoneNoteForm,
        CreateEditActivityGoalForm, ApproveDenyPTORequestForm,
        CreateEditPaidTimeOffLog, AddBusinessNoteForm,
        CreateEditBusinessDepartmentForm, CreateEditContactForm,
        AddContactNoteForm, CreateEditLeadForm, AddLeadNoteForm,
        SelectContactForm, AddDistinguishingValueChallenegeForm,
        AddTemplateDifferentiatingValuesForm, CreateEditTemplateDVForm,
        CreateEditDVCostItem, CreateEditOpportunity, EditLimitedUserProfileForm)
from timepiece.crm.models import (Business, Project, ProjectRelationship,
    UserProfile, PaidTimeOffLog, PaidTimeOffRequest, Milestone,
    ApprovedMilestone, MilestoneNote, ActivityGoal, BusinessNote,
    BusinessDepartment, Contact, ContactNote, BusinessAttachment, Lead,
    LeadNote, DistinguishingValueChallenge, TemplateDifferentiatingValue,
    LeadAttachment, DVCostItem, Opportunity, ProjectAttachment, Attribute,
    LimitedAccessUserProfile)
from timepiece.crm.utils import grouped_totals, project_activity_goals_with_progress
from timepiece.entries.models import Entry, Activity, Location
from timepiece.reports.forms import HourlyReportForm

from holidays.models import Holiday
from . import emails

try:
    from workflow.general_task.forms import SelectGeneralTaskForm
    from workflow.models import GeneralTask
except:
    pass

import workdays

from ajaxuploader.views import AjaxFileUploader
from ajaxuploader.backends.mongodb import MongoDBUploadBackend
# TODO: change this to be a utils.get_setting
from project_toolbox_main import settings as project_settings
from bson.objectid import ObjectId
import gridfs

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
                Entry.no_join.filter(pk__in=entries).update(status=Entry.UNVERIFIED)
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
    project_id = request.GET.get('project', None)
    # if request.GET.get('clear_project', None):
    #     project_id = None
    has_perm = request.user.has_perm('entries.view_entry_summary')
    if not (has_perm or user.pk == request.user.pk):
        return HttpResponseForbidden('Forbidden')


    from_date, to_date = utils.get_bimonthly_dates(datetime.date.today())
    FormClass = StatusUserDateForm if has_perm else StatusDateForm
    form = FormClass(request.GET or {'from_date': from_date, 'to_date': (to_date - relativedelta(days=1))})
    if form.is_valid():
        if has_perm:
            from_date, to_date, form_user, status = form.save()
            if form_user and request.GET.get('yearmonth', None):
                # Redirect to form_user's time sheet.
                # Do not use request.GET in urlencode to prevent redirect
                # loop caused by yearmonth parameter.
                url = reverse('view_user_timesheet', args=(form_user.pk,))
                request_data = {
                    'from_date': from_date,
                    'to_date': to_date - relativedelta(days=1),
                    'status': status,
                    # 'project': project_id,
                    'user': form_user.pk,  # Keep so that user appears in form.
                }
                url += '?{0}'.format(urlencode(request_data))
                return HttpResponseRedirect(url)
        else:  # User must be viewing their own time sheet; no redirect needed.
            from_date, to_date, status = form.save()
        if from_date is None or to_date is None:
            (from_date, to_date) = utils.get_bimonthly_dates(datetime.date.today())
        from_date = utils.add_timezone(from_date)
        to_date = utils.add_timezone(to_date)
    else:
        # Default to showing current bi-monthly period.
        from_date, to_date = utils.get_bimonthly_dates(datetime.date.today())
        status = None
    entries_qs = Entry.objects.filter(user=user, writedown=False)
    # DBROWNE - CHANGED THIS TO MATCH THE DESIRED RESULT FOR AAC ENGINEERING
    #month_qs = entries_qs.timespan(from_date, span='month')
    if status:
        entries_qs = entries_qs.filter(status=status)
    if project_id:
        entries_qs = entries_qs.filter(project__id=int(project_id))

    month_qs = entries_qs.timespan(from_date, to_date=to_date)
    extra_values = ('start_time', 'end_time', 'comments', 'seconds_paused',
            'id', 'location__name', 'project__name', 'activity__name',
            'status', 'mechanism', 'project__id')
    month_entries = month_qs.date_trunc('month', extra_values)
    # For grouped entries, back date up to the start of the period.
    first_week = utils.get_period_start(from_date)
    month_week = first_week + relativedelta(weeks=1)
    grouped_qs = entries_qs.timespan(first_week, to_date=to_date)
    intersection = grouped_qs.filter(
        start_time__lt=month_week, start_time__gte=from_date)
    # If the month of the first week starts in the previous
    # month and we dont have entries in that previous ISO
    # week, then update the first week to start at the first
    # of the actual month
    if not intersection and first_week.month < from_date.month:
        grouped_qs = entries_qs.timespan(from_date, to_date=to_date)
    totals = grouped_totals(grouped_qs) if month_entries else ''
    project_entries = month_qs.order_by().values(
        'project__name', 'project__id').annotate(sum=Sum('hours')).order_by('-sum')
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
        show_approve = all([
            verified_count + approved_count == total_statuses,
            verified_count > 0,
            total_statuses != 0,
        ])

    # # TODO: for some reason I have to loop over this in order to
    # # remedy an error... does not make any sense
    # for gt in totals:
    #     gt = gt
    # for week, week_totals, days in totals:
    #         print 'week', week, 'week_totals', week_totals, 'days', days
    return render(request, 'timepiece/user/timesheet/view.html', {
        'active_tab': active_tab or 'overview',
        'filter_form': form,
        'from_date': from_date,
        'to_date': to_date - relativedelta(days=1),
        'show_verify': show_verify,
        'show_approve': show_approve,
        'timesheet_user': user,
        'entries': month_entries,
        'grouped_totals': totals,
        'project_entries': project_entries,
        'summary': summary,
        'project': Project.objects.get(id=project_id) if project_id else None
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
        return HttpResponseForbidden('Forbidden: You cannot {0} this timesheet.'.format(action))

    try:
        (start, end) = utils.get_bimonthly_dates(datetime.date.today())
        from_date = request.GET.get('from_date', start.strftime('%Y-%m-%d'))
        from_date = utils.add_timezone(
            datetime.datetime.strptime(from_date, '%Y-%m-%d'))
        to_date = request.GET.get('to_date',
            (end - relativedelta(days=1)).strftime('%Y-%m-%d'))
        to_date = utils.add_timezone(
            datetime.datetime.strptime(to_date, '%Y-%m-%d')) + relativedelta(days=1)
        project_id = request.GET.get('project', None)
    except (ValueError, OverflowError, KeyError):
        raise Http404

    entries = Entry.no_join.filter(user=user_id,
                                   end_time__gte=from_date,
                                   end_time__lt=to_date,
                                   writedown=False)
    if project_id:
        entries = entries.filter(project__id=int(project_id))
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
        'from_date': from_date.date(),
        'to_date': to_date.date() - relativedelta(days=1),
        'user': user.id
    })
    if active_entries:
        msg = 'You cannot {0} this timesheet while the user {1} ' \
            'has an active entry. Please have them close any active ' \
            'entries.'.format(action, user.get_name_or_username())
        messages.error(request, msg)
        return redirect(return_url)
    if request.POST.get('do_action') == 'Yes':
        update_status = {
            'verify': 'verified',
            'approve': 'approved',
        }
        Entry.no_join.filter(pk__in=entries).update(status=update_status[action])
        messages.info(request, 'Your entries have been %s' % update_status[action])
        return redirect(return_url)
    hours = entries.all().aggregate(s=Sum('hours'))['s']
    if not hours:
        msg = 'You cannot {0} a timesheet with no hours'.format(action)
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
            return_url += '?%s' % urlencode(request_get)
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
            incl_writedowns = filter_form.cleaned_data['writedown']
        else:
            # date = utils.add_timezone(datetime.datetime.today())
            # from_date = utils.get_month_start(date).date()
            from_date, to_date = utils.get_bimonthly_dates(datetime.date.today())
            to_date = from_date + relativedelta(months=1)
            incl_billable = True
            incl_non_billable = True
            incl_writedowns = True

        from_datetime = datetime.datetime.combine(from_date,
            datetime.datetime.min.time())
        to_datetime = datetime.datetime.combine(to_date,
            datetime.datetime.min.time())

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

        if not incl_writedowns:
            entries_qs = entries_qs.filter(writedown=False)
        # entries_qs = entries_qs.timespan(from_date, span='month').filter(
        #     project=project
        # )
        extra_values = ('start_time', 'end_time', 'comments', 'seconds_paused',
                'id', 'location__name', 'project__name', 'activity__name',
                'status', 'writedown', 'activity__billable')
        month_entries = entries_qs.date_trunc('month', extra_values)
        total = entries_qs.aggregate(hours=Sum('hours'))['hours']
        user_entries = entries_qs.order_by().values('user__first_name', 'user__last_name')
        user_entries = user_entries.annotate(sum=Sum('hours')).order_by('-sum')
        activity_entries = entries_qs.order_by().values('activity__name')
        activity_entries = activity_entries.annotate(sum=Sum('hours')).order_by('-sum')
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
            'writedown': True,
            'paid_time_off': False,
            'unpaid_time_off': False,
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

        data['trunc'] = 'day'
        data['projects'] = []
        data['paid_time_off'] = False
        data['unpaid_time_off'] = False
        form = HourlyReportForm(data)
        for field in ['projects', 'paid_time_off', 'trunc', 'unpaid_time_off']:
            form.fields[field].widget = widgets.HiddenInput()
        return form


class ProjectTimesheetCSV(CSVViewMixin, ProjectTimesheet):

    def get_filename(self, context):
        project = self.object.code
        from_date_str = context['from_date'].strftime('%m-%d-%Y')
        to_date_str = context['to_date'].strftime('%m-%d-%Y')
        return '{0} {1} {2} timesheet'.format(project, from_date_str, to_date_str)

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
            'Comments',
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
                entry['comments'],
            ]
            rows.append(data)
        total = context['total']
        rows.append(('', '', '', '', '', '', 'Total:', total))
        return rows


# Businesses


@cbv_decorator(permission_required('crm.view_business'))
class ListBusinesses(SearchListView, CSVViewMixin):
    model = Business
    form_class = BusinessSearchForm
    paginate_by = 20
    redirect_if_one_result = True
    search_fields = ['name__icontains', 'description__icontains','businessnote__text__icontains']
    template_name = 'timepiece/business/list.html'

    def get(self, request, *args, **kwargs):
        self.export_business_list = request.GET.get('export_business_list', False)
        if self.export_business_list:
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
            return super(ListBusinesses, self).get(request, *args, **kwargs)

    def filter_form_valid(self, form, queryset):
        queryset = super(ListBusinesses, self).filter_form_valid(form, queryset)
        status = form.cleaned_data['status']
        classification = form.cleaned_data['classification']
        if status:
            queryset = queryset.filter(status=status)
        if classification:
            queryset = queryset.filter(classification=classification)
        return queryset

    def get_filename(self, context):
        request = self.request.GET.copy()
        search = request.get('search', '(empty)')
        return 'business_search_{0}'.format(search)

    def convert_context_to_csv(self, context):
        """Convert the context dictionary into a CSV file."""
        content = []
        business_list = context['business_list']
        if self.export_business_list:
            headers = ['Short Name', 'Business Name', 'Active?',
                       'Primary Contact', 'Description', 'Classification',
                       'Status', 'Phone', 'Fax', 'Website', 'Account Number',
                       'Industry', 'Ownership', 'Annual Revenue',
                       'Number of Employees', 'Ticket Symbol', 'Tags',
                       'Billing Street','Billing City', 'Billing State',
                       'Billing Zip', 'Billing Mailstop', 'Billing Country',
                       'Billing Latitude', 'Billing Longitude',
                       'Shipping Street', 'Shipping City', 'Shipping State',
                       'Shipping Zip', 'Shipping Mailstop', 'Shipping Country',
                       'Shipping Latitude', 'Shipping Longitude'
                       ]
            content.append(headers)
            for business in business_list:
                primary_contact = 'n/a'
                if business.primary_contact:
                    primary_contact = '%s %s, %s, %s' % (
                        business.primary_contact.first_name,
                        business.primary_contact.last_name,
                        business.primary_contact.office_phone,
                        business.primary_contact.email)
                row = [business.short_name, business.name, business.active,
                       primary_contact, business.description,
                       business.get_classification_display(),
                       business.get_status_display(), business.phone,
                       business.fax, business.website, business.account_number,
                       business.get_industry_display(), business.ownership,
                       business.annual_revenue, business.num_of_employees,
                       business.ticker_symbol,
                       ', '.join([str(t) for t in business.tags.all()]),
                       business.billing_street, business.billing_street_2, business.billing_city,
                       business.billing_state, business.billing_postalcode,
                       business.billing_mailstop, business.billing_country,
                       business.billing_lat, business.billing_lon,
                       business.shipping_street, business.shipping_city,
                       business.shipping_state, business.shipping_postalcode,
                       business.shipping_mailstop, business.shipping_country,
                       business.shipping_lat, business.shipping_lon]
                content.append(row)
        return content

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

@cbv_decorator(permission_required('crm.add_businessnote'))
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

@permission_required('workflow.view_business')
def business_upload_attachment(request, business_id):
    try:
        afu = AjaxFileUploader(MongoDBUploadBackend, db='business_attachments')
        hr = afu(request)
        content = json.loads(hr.content)
        memo = {'uploader': str(request.user),
                'file_id': str(content['_id']),
                'upload_time': str(datetime.datetime.now()),
                'filename': content['filename']}
        memo.update(content)
        # save attachment to ticket
        attachment = BusinessAttachment(
            business=Business.objects.get(id=int(business_id)),
            file_id=str(content['_id']),
            filename=content['filename'],
            upload_time=datetime.datetime.now(),
            uploader=request.user,
            description='n/a')
        attachment.save()
        return HttpResponse(json.dumps(memo),
                            content_type="application/json")
    except:
        print sys.exc_info(), traceback.format_exc()
    return hr

@permission_required('workflow.view_business')
def business_download_attachment(request, business_id, attachment_id):
    MONGO_DB_INSTANCE = project_settings.MONGO_CLIENT.business_attachments
    MONGO_DB_INSTANCE.authenticate( project_settings.MONGO_User,  project_settings.MONGO_PW)
    GRID_FS_INSTANCE = gridfs.GridFS(MONGO_DB_INSTANCE)
    try:
        business_attachment = BusinessAttachment.objects.get(
            business__id=business_id, id=attachment_id)
        f = GRID_FS_INSTANCE.get(ObjectId(business_attachment.file_id))
        return HttpResponse(f.read(), content_type=f.content_type)
    except:
        return HttpResponse("Business attachment could not be found.")


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

@login_required
def get_business_departments(request, business_id):
    data = []
    try:
        business = Business.objects.get(id=int(business_id))
        for department in business.businessdepartment_set.all().order_by('name'):
            data.append({'id': department.id,
                         'name': department.name})
    except:
        pass
    return HttpResponse(json.dumps(data),
                        content_type='application/json')

@login_required
def get_business_contacts(request, business_id):
    data = []
    try:
        business = Business.objects.get(id=int(business_id))
        for contact in Contact.objects.filter(user__isnull=True, business=business):
            data.append({'id': contact.id,
                         'name': '%s, %s' % (contact.last_name, contact.first_name)})
        for contact in Contact.objects.filter(user__profile__business=business):
            data.append({'id': contact.id,
                         'name': '%s, %s' % (contact.last_name, contact.first_name)})
        sorted_data = sorted(data, key=lambda k: k['name'])
    except:
        pass
    return HttpResponse(json.dumps(data),
                        content_type='application/json')

@cbv_decorator(permission_required('crm.change_business'))
class BusinessTags(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=501)

    def post(self, request, *args, **kwargs):
        business = Business.objects.get(id=int(kwargs['business_id']))
        tag = request.POST.get('tag')
        for t in tag.split(','):
            if len(t):
                business.tags.add(t)
        tags = [{'id': t.id,
                 'url': reverse('similar_items', args=(t.id,)),
                 'name':t.name} for t in business.tags.all()]
        return HttpResponse(json.dumps({'tags': tags}),
                            content_type="application/json",
                            status=200)
@cbv_decorator(permission_required('crm.change_business'))
class RemoveBusinessTag(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=501)

    def post(self, request, *args, **kwargs):
        if request.user.is_superuser or bool(len(request.user.groups.filter(id=8))):
            business = Business.objects.get(id=int(kwargs['business_id']))
            tag = request.POST.get('tag')
            if len(tag):
                business.tags.remove(tag)
        tags = [{'id': t.id,
                 'url': reverse('similar_items', args=(t.id,)),
                 'name':t.name} for t in business.tags.all()]
        return HttpResponse(json.dumps({'tags': tags}),
                            content_type="application/json",
                            status=200)

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
        return self.request.GET.get('next', None) or reverse('dashboard')


@cbv_decorator(permission_required('auth.view_user'))
class ListUsers(SearchListView):
    model = User
    paginate_by = 20
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
        kwargs.update({'add_project_form': SelectProjectForm(),
                       'user_id': int(self.kwargs['user_id'])})
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
        if up.limited:
            up.limited.delete()
        up.delete()
        return super(DeleteUser, self).delete(request, *args, **kwargs)


@cbv_decorator(permission_required('auth.change_user'))
class EditUser(UpdateView):
    model = User
    form_class = EditUserForm
    template_name = 'timepiece/user/create_edit.html'
    pk_url_kwarg = 'user_id'

@cbv_decorator(permission_required('crm.change_limitedaccessuserprofile'))
class CreateLimitedAccessUserProfile(CreateView):
    model = LimitedAccessUserProfile
    form_class = EditLimitedUserProfileForm
    template_name = 'timepiece/user/edit_profile.html'

    def get_context_data(self, **kwargs):
        context = super(CreateLimitedAccessUserProfile, self).get_context_data(**kwargs)
        context['profile'] = User.objects.get(id=int(self.kwargs['user_id'])).profile
        return context

    def get_form(self, *args, **kwargs):
        form = super(CreateLimitedAccessUserProfile, self).get_form(*args, **kwargs)
        form.fields['profile'].initial = User.objects.get(id=int(self.kwargs['user_id'])).profile.id
        form.fields['profile'].widget = widgets.HiddenInput()
        return form

    def get_success_url(self):
        return reverse_lazy('view_user', args=(int(self.kwargs['user_id']),))


@cbv_decorator(permission_required('crm.change_limitedaccessuserprofile'))
class EditLimitedAccessUserProfile(UpdateView):
    model = LimitedAccessUserProfile
    form_class = EditLimitedUserProfileForm
    template_name = 'timepiece/user/edit_profile.html'
    pk_url_kwarg = 'profile_id'

    def get_success_url(self):
        return reverse_lazy('view_user', args=(int(self.kwargs['user_id']),))

# Projects


@cbv_decorator(permission_required('crm.view_project'))
class ListProjects(SearchListView, CSVViewMixin):
    model = Project
    form_class = ProjectSearchForm
    paginate_by = 20
    redirect_if_one_result = True
    search_fields = ['name__icontains', 'description__icontains', 'code__icontains',
    'point_person__first_name__icontains', 'point_person__last_name__icontains']
    template_name = 'timepiece/project/list.html'

    def get(self, request, *args, **kwargs):
        if len(request.GET.keys()) == 0:
            return HttpResponseRedirect(reverse('list_projects') \
                + '?status=' + str(get_setting('TIMEPIECE_DEFAULT_PROJECT_STATUS')))
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

            # this is paginating results...
            context = self.get_context_data(form=self.form,
                object_list=self.object_list)
            # so I'm overriding the project list here
            context['project_list'] = self.object_list

            return kls.render_to_response(self, context)
        else:
            return super(ListProjects, self).get(request, *args, **kwargs)

    def filter_form_valid(self, form, queryset):
        queryset = super(ListProjects, self).filter_form_valid(form, queryset)
        status = form.cleaned_data['status']
        if status:
            queryset = queryset.filter(status__in=status)
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

            # milestones added.  m miles stones and n contracts, so have to shift headers dynamically. maybe this should be a separate export
            max_contracts = 1
            max_milestones = 1
            for project in project_list:
                max_contracts = max(max_contracts,len(project.contracts.all()))
                max_milestones = max(max_milestones,len(project.milestones.all()))

            headers = ['Project Code', 'Project Name', 'Type',
                'Project Department', 'Business', 'Business Department','External ID Code',
                'Client Primary', 'Status', 'Billable', 'Finder', 'Minder',
                'Binder', 'Target Internal Completion', 'Required Completion',
                'Target Open', 'Start', 'Turn-In', 'Description', 'Tags',
                'Contracts --> '+str(max_contracts)]+['']*(max_contracts-1)+['Milestones --> '+str(max_milestones)]
            content.append(headers)

            for project in project_list:
                # collect milestones
                # when we upgrae Django, we can do a .filter().first() instead of this business
                tic_ms = Milestone.objects.filter(project=project, name='Target Internal Completion')
                tic_ms = tic_ms[0] if len(tic_ms) else None
                required_ms = Milestone.objects.filter(project=project, name='Required Completion')
                required_ms = required_ms[0] if len(required_ms) else None
                target_open_ms = Milestone.objects.filter(project=project, name='Target Open')
                target_open_ms = target_open_ms[0] if len(target_open_ms) else None
                start_ms = Milestone.objects.filter(project=project, name='Start')
                start_ms = start_ms[0] if len(start_ms) else None
                turn_in_ms = Milestone.objects.filter(project=project, name='Turn-In')
                turn_in_ms = turn_in_ms[0] if len(turn_in_ms) else None

                row = [project.code, project.name, str(project.type),
                    project.get_project_department_display(),
                    '%s:%s'%(project.business.short_name, project.business.name),
                    project.business_department.name if project.business_department else '',
                    project.ext_code if project.ext_code else '',
                    '%s %s' % (project.client_primary_poc.first_name, project.client_primary_poc.last_name) if project.client_primary_poc else '',
                    project.status, project.billable, str(project.finder),
                    str(project.point_person), str(project.binder),
                    tic_ms.due_date if tic_ms else '',
                    required_ms.due_date if required_ms else '',
                    target_open_ms.due_date if target_open_ms else '',
                    start_ms.due_date if start_ms else '',
                    turn_in_ms.due_date if turn_in_ms else '',
                    project.description, ', '.join([t.name.strip() for t in project.tags.all()])]

                project_contract_count=len(project.contracts.all())
                for contract in project.contracts.all():
                    row.append(str(contract))
                for blank_space in range(max_contracts - project_contract_count):
                    row.append('')
                for milestone in project.milestones.all():
                    row.append(str(milestone))
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

        context = super(ViewProject, self).get_context_data(**kwargs)
        try:
            context['add_general_task_form'] = SelectGeneralTaskForm()
        except:
            pass

        return context


@cbv_decorator(permission_required('crm.add_project'))
class CreateProject(CreateView):
    model = Project
    form_class = CreateProjectForm
    template_name = 'timepiece/project/create_edit.html'

    def get_form_kwargs(self):
        kwargs = super(CreateProject, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs


@cbv_decorator(permission_required('crm.delete_project'))
class DeleteProject(DeleteView):
    model = Project
    success_url = reverse_lazy('list_projects')
    pk_url_kwarg = 'project_id'
    template_name = 'timepiece/delete_object.html'

@permission_required('crm.delete_project')
def archive_project(request,project_id):
    project=Project.objects.get(id=project_id)
    if project:
        archived_status = Attribute.objects.get(label='Archived')
        project.status=archived_status
        project.save()
    return HttpResponseRedirect(reverse('list_projects'))

@cbv_decorator(permission_required('crm.change_project'))
class EditProject(UpdateView):
    model = Project
    form_class = EditProjectForm
    template_name = 'timepiece/project/create_edit.html'
    pk_url_kwarg = 'project_id'

@cbv_decorator(permission_required('crm.add_projectrelationship'))
class AddProjectGeneralTask(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=501)

    def post(self, request, *args, **kwargs):
        try:
            project = Project.objects.get(id=int(kwargs['project_id']))
            general_task = SelectGeneralTaskForm(request.POST).get_general_task()
            if general_task.project is None:
                general_task.project = project
                general_task.save()
            else:
                msg = '%s already belongs to Project <a href="' + \
                reverse('view_project', args=(general_task.project.id,)) + \
                '">%s.  Please remove it from that Project before ' + \
                'associating with this one.' % (
                    general_task.form_id, general_task.project.code)
                messages.error(request, msg)
        except:
            print sys.exc_info(), traceback.format_exc()
        finally:
            return HttpResponseRedirect(request.GET.get('next', None)
                or reverse_lazy('view_project', args=(project.id,)))

@cbv_decorator(permission_required('crm.add_projectrelationship'))
class RemoveProjectGeneralTask(View):

    def get(self, request, *args, **kwargs):
        try:
            project = Project.objects.get(id=int(kwargs['project_id']))
            general_task_id = request.GET.get('general_task_id')
            general_task = GeneralTask.objects.get(id=int(general_task_id))
            general_task.project = None
            general_task.save()
        except:
            print sys.exc_info(), traceback.format_exc()
        finally:
            return HttpResponseRedirect(request.GET.get('next', None)
                or reverse_lazy('view_project', args=(project.id,)))

@cbv_decorator(permission_required('crm.change_project'))
class ProjectTags(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=501)

    def post(self, request, *args, **kwargs):
        project = Project.objects.get(id=int(kwargs['project_id']))
        tag = request.POST.get('tag')
        for t in tag.split(','):
            if len(t):
                project.tags.add(t)
        tags = [{'id': t.id,
                 'url': reverse('similar_items', args=(t.id,)),
                 'name':t.name} for t in project.tags.all()]
        return HttpResponse(json.dumps({'tags': tags}),
                            content_type="application/json",
                            status=200)

@cbv_decorator(permission_required('crm.change_project'))
class RemoveProjectTag(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=501)

    def post(self, request, *args, **kwargs):
        if request.user.is_superuser or bool(len(request.user.groups.filter(id=8))):
            project = Project.objects.get(id=int(kwargs['project_id']))
            tag = request.POST.get('tag')
            if len(tag):
                project.tags.remove(tag)
        tags = [{'id': t.id,
                 'url': reverse('similar_items', args=(t.id,)),
                 'name':t.name} for t in project.tags.all()]
        return HttpResponse(json.dumps({'tags': tags}),
                            content_type="application/json",
                            status=200)

# User-project relationships


@cbv_decorator(permission_required('crm.add_projectrelationship'))
@cbv_decorator(csrf_exempt)
@cbv_decorator(transaction.atomic)
class CreateRelationship(View):

    def post(self, request, *args, **kwargs):
        user = self.get_user()
        project = self.get_project()
        if user and project:
            ProjectRelationship.objects.get_or_create(user=user, project=project)
        redirect_to = request.GET.get('next', None) or reverse('dashboard')
        return HttpResponseRedirect(redirect_to)

    def get_user(self):
        user_id = self.request.GET.get('user_id', None)
        if user_id:
            return get_object_or_404(User, pk=user_id)
        return SelectUserForm(self.request.POST).get_user()

    def get_project(self):
        project_id = self.request.GET.get('project_id', None)
        if project_id:
            return get_object_or_404(Project, pk=project_id)
        return SelectProjectForm(self.request.POST).get_project()


class RelationshipObjectMixin(object):
    """Handles retrieving and redirecting for ProjectRelationship objects."""

    def get_object(self, queryset=None):
        queryset = self.get_queryset() if queryset is None else queryset
        user_id = self.request.GET.get('user_id', None)
        project_id = self.request.GET.get('project_id', None)
        return get_object_or_404(self.model, user__id=user_id, project__id=project_id)

    def get_success_url(self):
        return self.request.GET.get('next', self.object.project.get_absolute_url())


@cbv_decorator(permission_required('crm.change_projectrelationship'))
@cbv_decorator(transaction.atomic)
class EditRelationship(RelationshipObjectMixin, UpdateView):
    model = ProjectRelationship
    template_name = 'timepiece/relationship/edit.html'
    form_class = EditProjectRelationshipForm


@cbv_decorator(permission_required('crm.delete_projectrelationship'))
@cbv_decorator(csrf_exempt)
@cbv_decorator(transaction.atomic)
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
        data['pto_approvals'] = PaidTimeOffRequest.objects.filter(Q(status=PaidTimeOffRequest.PENDING) | Q(status=PaidTimeOffRequest.APPROVED) | Q(status=PaidTimeOffRequest.MODIFIED))
        data['pto_all_history'] = PaidTimeOffLog.objects.filter(pto=True).order_by('user_profile', '-date')
        data['upto_all_history'] = PaidTimeOffLog.objects.filter(pto=False).order_by('user_profile', '-date')
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

    if request.user.has_perm('crm.view_current_pto'):
        data['current_pto'] = Group.objects.get(id=1).user_set.all().filter(is_active=True, profile__earns_pto=True).order_by('last_name', 'first_name')
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
        instance = form.instance
        instance.approver = None
        instance.approval_date = None
        instance.approver_comment = ''
        instance.process_date = None
        instance.processor = None

        if not instance.user_profile.earns_pto:
            instance.pto = False

        if instance.status in [PaidTimeOffRequest.APPROVED,
            PaidTimeOffRequest.PROCESSED, PaidTimeOffRequest.MODIFIED]:

            # delete existing references to this Time Off Request
            for ptol in PaidTimeOffLog.objects.filter(
                pto_request=instance):

                Entry.objects.filter(pto_log=ptol).delete()
                ptol.delete()

            instance.status = PaidTimeOffRequest.MODIFIED

            emails.updated_pto(instance,
                reverse('pto_request_details', args=(instance.id,)),
                reverse('approve_pto_request', args=(instance.id,)),
                reverse('deny_pto_request', args=(instance.id,)),
            )

        else:
            instance.status = PaidTimeOffRequest.PENDING

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

        # check to see if user earns holiday pay, if not, they can take use it for pto
        if up.earns_holiday_pay:
            for year in range(form.instance.pto_start_date.year, form.instance.pto_end_date.year+1):
                holiday_dates = [h['date'] for h in Holiday.get_holidays_for_year(year, {'paid_holiday':True})]
                holidays.extend(holiday_dates)
        # get number of workdays found in between the start and stop dates
        num_workdays = workdays.networkdays(form.instance.pto_start_date,
                                            form.instance.pto_end_date,
                                            holidays)
        num_workdays = max(num_workdays, 1)

        # add PTO log entries
        # if form.instance.pto:
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
                                     pto_request=form.instance,
                                     pto=form.instance.pto)
            pto_log.save()

            # if pto entry, add timesheet entry
            if form.instance.amount > 0:
                if form.instance.pto:
                    entry = Entry(user=form.instance.user_profile.user,
                                  project=Project.objects.get(id=utils.get_setting('TIMEPIECE_PTO_PROJECT')),
                                  activity=Activity.objects.get(id=24),
                                  location=Location.objects.get(id=3),
                                  start_time=start_time,
                                  end_time=end_time,
                                  comments='Approved PTO %s.' % form.instance.pk,
                                  hours=hours,
                                  pto_log=pto_log,
                                  mechanism=Entry.PTO)
                    entry.save()
                else:
                    entry = Entry(user=form.instance.user_profile.user,
                                  project=Project.objects.get(id=utils.get_setting('TIMEPIECE_UPTO_PROJECT')),
                                  activity=Activity.objects.get(id=41),
                                  location=Location.objects.get(id=3),
                                  start_time=start_time,
                                  end_time=end_time,
                                  comments='Approved UPTO %s.' % form.instance.pk,
                                  hours=hours,
                                  pto_log=pto_log,
                                  mechanism=Entry.PTO)
                                  #status=Entry.APPROVED)
                    entry.save()

        emails.approved_pto(form.instance,
            reverse('pto_request_details', args=(form.instance.id,)))

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

        emails.denied_pto(form.instance,
            reverse('pto_request_details', args=(form.instance.id,)))

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
        return reverse('pto', args=('all_history',))

@cbv_decorator(permission_required('crm.change_paidtimeofflog'))
class EditPTOLogEntry(UpdateView):
    model = PaidTimeOffLog
    form_class = CreateEditPaidTimeOffLog
    pk_url_kwarg = 'pto_log_id'
    template_name = 'timepiece/pto/create-edit-log.html'

    def get_success_url(self):
        return reverse('pto', args=('all_history',))

@cbv_decorator(permission_required('crm.delete_paidtimeofflog'))
class DeletePTOLogEntry(DeleteView):
    model = PaidTimeOffLog
    pk_url_kwarg = 'pto_log_id'
    template_name = 'timepiece/delete_object.html'

    def get_success_url(self):
        return '/timepiece/project/%d' % int(self.kwargs['project_id'])

    def get_success_url(self):
        return reverse('pto', args=('all_history',))

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

    def get_context_data(self, **kwargs):
        context = super(ViewMilestone, self).get_context_data(**kwargs)
        # context['project'] = Project.objects.get(id=int(self.kwargs['project_id']))
        context['add_milestone_note_form'] = AddMilestoneNoteForm()
        return context

@cbv_decorator(permission_required('crm.add_milestone'))
class CreateMilestone(CreateView):
    model = Milestone
    form_class = CreateEditMilestoneForm
    template_name = 'timepiece/project/milestone/create_edit.html'

    def get_context_data(self, **kwargs):
        context = super(CreateMilestone, self).get_context_data(**kwargs)
        context['project'] = Project.objects.get(id=int(self.kwargs['project_id']))
        return context

    def form_valid(self, form):
        form.instance.project = Project.objects.get(id=int(self.kwargs['project_id']))
        form.instance.author = self.request.user
        form.instance.editor = self.request.user
        return super(CreateMilestone, self).form_valid(form)

    def get_success_url(self):
        return '/timepiece/project/%d' % int(self.kwargs['project_id'])


@cbv_decorator(permission_required('crm.change_milestone'))
class EditMilestone(UpdateView):
    model = Milestone
    form_class = CreateEditMilestoneForm
    template_name = 'timepiece/project/milestone/create_edit.html'
    pk_url_kwarg = 'milestone_id'

    def get_context_data(self, **kwargs):
        context = super(EditMilestone, self).get_context_data(**kwargs)
        context['project'] = Project.objects.get(id=int(self.kwargs['project_id']))
        return context

    def form_valid(self, form):
        form.instance.editor = self.request.user
        if form.has_changed():
            form.instance.status = Milestone.MODIFIED
            form.instance.approver = None
            form.instance.approval_date = None
        return super(EditMilestone, self).form_valid(form)

    def get_success_url(self):
        return '/timepiece/project/%d' % int(self.kwargs['project_id'])


@cbv_decorator(permission_required('crm.add_milestonenote'))
class AddMilestoneNote(View):

    def post(self, request, *args, **kwargs):
        user = self.request.user
        milestone = Milestone.objects.get(id=int(kwargs['milestone_id']))
        note = MilestoneNote(milestone=milestone,
                             author=user,
                             text=request.POST.get('text', ''))
        if len(note.text):
            note.save()
        return HttpResponseRedirect(request.GET.get('next', None) or
            reverse('view_milestone', args=(milestone.id,)))


@cbv_decorator(permission_required('crm.approve_milestone'))
class ApproveMilestone(UpdateView):
    model = Milestone
    form_class = ApproveMilestoneForm
    template_name = 'timepiece/project/milestone/approve.html'
    pk_url_kwarg = 'milestone_id'

    def get_context_data(self, **kwargs):
        context = super(ApproveMilestone, self).get_context_data(**kwargs)
        context['project'] = Project.objects.get(id=int(self.kwargs['project_id']))
        context['add_milestone_note_form'] = AddMilestoneNoteForm()
        return context

    def form_valid(self, form):
        # if the user added a note, save it here
        text = self.request.POST.get('note', '')
        if text:
            note = MilestoneNote(
                milestone=form.instance,
                text=text,
                author=self.request.user)
            note.save()

        # set status as approved or pending
        if self.request.POST.get('approve', False):
            form.instance.approver = self.request.user
            form.instance.status = Milestone.APPROVED
            form.instance.approval_date = datetime.datetime.now()

            # record keeping
            ApprovedMilestone.objects.create(
                milestone=form.instance,
                project=form.instance.project,
                name=form.instance.name,
                description=form.instance.description,
                due_date=form.instance.due_date,
                author=form.instance.author,
                created=form.instance.created,
                editor=form.instance.editor,
                modified=form.instance.modified,
                status=form.instance.status,
                approver=form.instance.approver,
                approval_date=form.instance.approval_date
            )

        elif self.request.POST.get('deny', False):
            form.instance.approver = self.request.user
            form.instance.status = Milestone.DENIED
            form.instance.approval_date = datetime.datetime.now()

        return super(ApproveMilestone, self).form_valid(form)

    def get_success_url(self):
        return '/timepiece/project/%d' % int(self.kwargs['project_id'])

@cbv_decorator(permission_required('crm.approve_milestone'))
class ApproveAllProjectMilestones(UpdateView):
    model = Project
    form_class = ApproveMilestoneForm
    template_name = 'timepiece/project/approve_milestones.html'
    pk_url_kwarg = 'project_id'

    def form_valid(self, form):
        project = self.object
        for milestone in project.milestone_set.filter(status__in=[Milestone.NEW, Milestone.MODIFIED]):
            milestone.approver = self.request.user
            milestone.status = Milestone.APPROVED
            milestone.approval_date = datetime.datetime.now()
            milestone.save()

            # record keeping
            ApprovedMilestone.objects.create(
                milestone=milestone,
                project=milestone.project,
                name=milestone.name,
                description=milestone.description,
                due_date=milestone.due_date,
                author=milestone.author,
                created=milestone.created,
                editor=milestone.editor,
                modified=milestone.modified,
                status=milestone.status,
                approver=milestone.approver,
                approval_date=milestone.approval_date
            )

        return super(ApproveAllProjectMilestones, self).form_valid(form)

    def get_success_url(self):
        return '/timepiece/project/%d' % int(self.object.id)


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
    template_name = 'timepiece/project/activity_goal/create_edit.html'

    def get_context_data(self, **kwargs):
        context = super(CreateActivityGoal, self).get_context_data(**kwargs)
        context['project'] = Project.objects.get(id=int(self.kwargs['project_id']))
        return context

    def get_initial(self):
        employee = self.request.GET.get('employee', None)
        activity = self.request.GET.get('activity', None)
        start_date = self.request.GET.get('start_date', datetime.date.today())
        end_date = self.request.GET.get('end_date', None)
        try:
            project = Project.objects.get(id=int(self.kwargs['project_id']))
        except:
            # redirect somewhere else with an error
            pass
        initial = {'employee': employee,
                   'activity': activity,
                   'date': start_date,
                   'end_date': end_date,
                   'goal_hours': self.request.GET.get('goal_hours', None)}
        if employee and activity and project and start_date==datetime.date.today():
            # find the initial date of charging
            try:
                e = Entry.objects.filter(user__id=employee,
                    activity__id=activity, project=project
                    ).order_by('-start_time')[0:1].get()
                initial['date'] = e.start_time.date()
            except ObjectDoesNotExist:
                pass

        return initial

    def get_form(self, *args, **kwargs):
        form = super(CreateActivityGoal, self).get_form(*args, **kwargs)
        project = Project.objects.get(id=int(self.kwargs['project_id']))
        if project.activity_group:
            activities = [(a.id, a.name) for a in project.activity_group.activities.all()]
            form.fields['activity'].choices = activities

        employee_choices = [(None, '--- AAC EMPLOYEES ---')]
        exclude = []
        for u in Group.objects.get(id=1).user_set.filter(
            is_active=True).order_by('last_name', 'first_name'):

            employee_choices.append((u.pk, '%s, %s'%(u.last_name, u.first_name)))
            exclude.append(u.pk)

        employee_choices.append((None, '--- EXTERNAL USERS ---'))
        for u in User.objects.filter(is_active=True).exclude(id__in=exclude
            ).order_by('last_name', 'first_name'):

            employee_choices.append((u.pk, '%s, %s'%(u.last_name, u.first_name)))
            # exclude.append(u.pk)

        employee_choices.append((None, '--- INACTIVE USERS ---'))
        for u in User.objects.all().exclude(id__in=exclude
            ).order_by('last_name', 'first_name'):

            employee_choices.append((u.pk, '%s, %s'%(u.last_name, u.first_name)))

        form.fields['employee'].choices = employee_choices
        return form

    def form_valid(self, form):
        form.instance.project = Project.objects.get(id=int(self.kwargs['project_id']))
        return super(CreateActivityGoal, self).form_valid(form)

    def get_success_url(self):
        return self.request.GET.get('next', None) or reverse_lazy(
            'view_project', args=(int(self.kwargs['project_id']),))


@cbv_decorator(permission_required('crm.change_activitygoal'))
class EditActivityGoal(UpdateView):
    model = ActivityGoal
    form_class = CreateEditActivityGoalForm
    template_name = 'timepiece/project/activity_goal/create_edit.html'
    pk_url_kwarg = 'activity_goal_id'


    def get_context_data(self, **kwargs):
        context = super(EditActivityGoal, self).get_context_data(**kwargs)
        context['project'] = Project.objects.get(id=int(self.kwargs['project_id']))
        return context

    def get_form(self, *args, **kwargs):
        form = super(EditActivityGoal, self).get_form(*args, **kwargs)
        project = Project.objects.get(id=int(self.kwargs['project_id']))
        if project.activity_group is not None:
            activities = [(a.id, a.name) for a in project.activity_group.activities.all()]
            form.fields['activity'].choices = activities

        employee_choices = [(None, '--- AAC EMPLOYEES ---')]
        exclude = []
        for u in Group.objects.get(id=1).user_set.filter(
            is_active=True).order_by('last_name', 'first_name'):

            employee_choices.append((u.pk, '%s, %s'%(u.last_name, u.first_name)))
            exclude.append(u.pk)

        employee_choices.append((None, '--- EXTERNAL USERS ---'))
        for u in User.objects.filter(is_active=True).exclude(id__in=exclude
            ).order_by('last_name', 'first_name'):

            employee_choices.append((u.pk, '%s, %s'%(u.last_name, u.first_name)))
            exclude.append(u.pk)

        employee_choices.append((None, '--- INACTIVE USERS ---'))
        for u in User.objects.all().exclude(id__in=exclude
            ).order_by('last_name', 'first_name'):

            employee_choices.append((u.pk, '%s, %s'%(u.last_name, u.first_name)))

        form.fields['employee'].choices = employee_choices

        return form

    def get_success_url(self):
        return self.request.GET.get('next', None) or reverse_lazy(
            'view_project', args=(int(self.kwargs['project_id']),))


@cbv_decorator(permission_required('crm.delete_activitygoal'))
class DeleteActivityGoal(DeleteView):
    model = ActivityGoal
    pk_url_kwarg = 'activity_goal_id'
    template_name = 'timepiece/delete_object.html'

    def get_success_url(self):
        return '/timepiece/project/%d' % (int(self.kwargs['project_id']),)

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
    #         return HttpResponse(json.dumps(data), status=200, content_type='application/json')
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
                end_date = max(Milestone.objects.filter(project=project).order_by('-due_date')[0].due_date,
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
        for ag in ActivityGoal.objects.filter(project=project).order_by('employee__last_name', 'employee__first_name', 'goal_hours'):
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
            ag_len = len(ag_temp[i])
            k = 0
            day_totals = []
            for j in range((end_date - start_date).days):
                cur_date = start_date + datetime.timedelta(days=j)
                day_totals.append(0.0)
                while k < ag_len:
                    if ag_temp[i][k].date <= cur_date:
                        day_totals[j] += float(ag_temp[i][k].goal_hours)
                        k += 1
                    else:
                        break
            # print numpy.cumsum(day_totals)

            activity_goals[i].extend(list(numpy.cumsum(day_totals)))

        # for i in range(len(ag_temp)):
        #     if len(ag_temp[i]) == 0:
        #         continue
        #     ag_hours = []
        #     for employee, ags in groupby(ag_temp[i], lambda x: x.employee):
        #         last_date = start_date
        #         vals = []
        #         for ag in ags:
        #             gh = float(ag.goal_hours)
        #             for j in range((ag.end_date - last_date).days + 1):
        #                 vals.append(gh)
        #             last_date = ag.end_date
        #         ag_hours.append(vals)

        #     max_len = len(ag_hours[0])
        #     for ag_hours_employee in ag_hours:
        #         max_len = max(max_len, len(ag_hours_employee))
        #     for ag_hours_employee in ag_hours:
        #         val = ag_hours_employee[-1]
        #         while len(ag_hours_employee) < max_len:
        #             ag_hours_employee.append(val)
        #     activity_goals[i].extend(list(numpy.sum(ag_hours, axis=0)))

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
        return HttpResponse(json.dumps(data), status=200, content_type='application/json')
    except:
        print sys.exc_info(), traceback.format_exc()
        return HttpResponse(json.dumps({}), status=200, content_type='application/json')

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
                     'business_department__name__icontains','contactnote__text__icontains']
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

@cbv_decorator(permission_required('crm.add_contactnote'))
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

@cbv_decorator(permission_required('crm.add_contactnote'))
class ContactTags(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=200)

    def post(self, request, *args, **kwargs):
        contact = Contact.objects.get(id=int(kwargs['contact_id']))
        tag = request.POST.get('tag')
        for t in tag.split(','):
            if len(t):
                contact.tags.add(t)
        tags = [{'id': t.id,
                 'url': reverse('similar_items', args=(t.id,)),
                 'name':t.name} for t in contact.tags.all()]
        return HttpResponse(json.dumps({'tags': tags}),
                            content_type="application/json",
                            status=200)

@cbv_decorator(permission_required('crm.delete_contact'))
class RemoveContactTag(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=501)

    def post(self, request, *args, **kwargs):
        if request.user.is_superuser or bool(len(request.user.groups.filter(id=8))):
            contact = Contact.objects.get(id=int(kwargs['contact_id']))
            tag = request.POST.get('tag')
            if len(tag):
                contact.tags.remove(tag)
        tags = [{'id': t.id,
                 'url': reverse('similar_items', args=(t.id,)),
                 'name':t.name} for t in contact.tags.all()]
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


""" LEADS """
@cbv_decorator(permission_required('crm.view_lead'))
class ListLeads(SearchListView, CSVViewMixin):
    model = Lead
    redirect_if_one_result = True
    search_fields = ['title__icontains',
                     'primary_contact__first_name__icontains',
                     'primary_contact__last_name__icontains',
                     'primary_contact__email__icontains',
                     'primary_contact__business__name__icontains','leadnote__text__icontains']
    template_name = 'timepiece/lead/list.html'

    def get(self, request, *args, **kwargs):
        self.export_lead_list = request.GET.get('export_lead_list', False)
        self.export_lead_list_general_tasks = request.GET.get('export_lead_list_general_tasks', False)
        if self.export_lead_list:
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

        elif self.export_lead_list_general_tasks:
            kls = CSVViewMixin

            form_class = self.get_form_class()
            self.form = self.get_form(form_class)
            self.object_list = self.get_queryset()
            self.object_list = self.filter_results(self.form, self.object_list)

            self.object_list = GeneralTask.objects.filter(
                lead__in=self.object_list).order_by('lead__status',
                'lead__title', 'lead', 'form_id')

            allow_empty = self.get_allow_empty()
            if not allow_empty and len(self.object_list) == 0:
                raise Http404("No results found.")

            context = self.get_context_data(form=self.form,
                object_list=self.object_list)

            return kls.render_to_response(self, context)

        else:
            return super(ListLeads, self).get(request, *args, **kwargs)

    # def filter_form_valid(self, form, queryset):
    #     queryset = super(ListContacts, self).filter_form_valid(form, queryset)
    #     status = form.cleaned_data['status']
    #     if status:
    #         queryset = queryset.filter(status=status)
    #     return queryset

    def get_filename(self, context):
        if self.export_lead_list:
            request = self.request.GET.copy()
            search = request.get('search', '(empty)')
            return 'lead_search_{0}'.format(search)
        elif self.export_lead_list_general_tasks:
            request = self.request.GET.copy()
            search = request.get('search', '(empty)')
            return 'lead_search_{0}_general_tasks'.format(search)

    def convert_context_to_csv(self, context):
        """Convert the context dictionary into a CSV file."""
        content = []
        lead_list = context['lead_list'] if 'lead_list' in context else []
        general_task_list = context['generaltask_list'] if 'generaltask_list' in context else []
        if self.export_lead_list:
            headers = ['Lead ID',
                       'Title',
                       'Status',
                       '7 Day Status Changes',
                       'Project Count',
                       'AAC Primary',
                       'Primary Contact Salutaton',
                       'Primary Contact First Name',
                       'Primary Contact Last Name',
                       'Primary Contact Title',
                       'Primary Contact Email',
                       'Primary Contact Office Phone',
                       'Primary Contact Mobile Phone',
                       'Primary Contact Home Phone',
                       'Primary Contact Other Phone',
                       'Primary Contact Fax',
                       'Primary Contact Business Name',
                       'Primary Contact Business Department Name',
                       'Primary Contact Assistant Name',
                       'Primary Contact Assistant Phone',
                       'Primary Contact Assistant Email',
                       'Primary Contact Mailing Street',
                       'Primary Contact Mailing City',
                       'Primary Contact Mailing State',
                       'Primary Contact Mailing Postal Code',
                       'Primary Contact Mailing Mailstop',
                       'Primary Contact Mailing Country',
                       'Primary Contact Mailing Latitude',
                       'Primary Contact Mailing Longitude',
                       'Primary Contact Other Street',
                       'Primary Contact Other City',
                       'Primary Contact Other State',
                       'Primary Contact Other Postal Code',
                       'Primary Contact Other Mailstop',
                       'Primary Contact Other Country',
                       'Primary Contact Other Latitude',
                       'Primary Contact Other Longitude',
                       'Primary Contact Opted Out of Email',
                       'Primary Contact Opted Out of Fax',
                       'Primary Contact DO NOT CALL',
                       'Primary Contact Birthday',
                       'Lead Source Email', 'Tags -->']
            content.append(headers)
            for lead in lead_list:
                if lead.primary_contact:
                    row = [lead.id,
                           lead.title,
                           lead.get_status_display(),
                           str(len(lead.leadhistory_set.filter(created_at__gte=datetime.datetime.now()-datetime.timedelta(days=7)))),
                           str(len(lead.get_projects)),
                           '%s %s' % (lead.aac_poc.first_name, lead.aac_poc.last_name),
                           lead.primary_contact.salutation,
                           lead.primary_contact.first_name,
                           lead.primary_contact.last_name,
                           lead.primary_contact.title,
                           lead.primary_contact.email,
                           lead.primary_contact.office_phone,
                           lead.primary_contact.mobile_phone,
                           lead.primary_contact.home_phone,
                           lead.primary_contact.other_phone,
                           lead.primary_contact.fax,
                           lead.primary_contact.business,
                           lead.primary_contact.business_department,
                           lead.primary_contact.assistant_name,
                           lead.primary_contact.assistant_phone,
                           lead.primary_contact.assistant_email,
                           lead.primary_contact.mailing_street,
                           lead.primary_contact.mailing_city,
                           lead.primary_contact.mailing_state,
                           lead.primary_contact.mailing_postalcode,
                           lead.primary_contact.mailing_mailstop,
                           lead.primary_contact.mailing_country,
                           lead.primary_contact.mailing_lat,
                           lead.primary_contact.mailing_lon,
                           lead.primary_contact.other_street,
                           lead.primary_contact.other_city,
                           lead.primary_contact.other_state,
                           lead.primary_contact.other_postalcode,
                           lead.primary_contact.other_mailstop,
                           lead.primary_contact.other_country,
                           lead.primary_contact.other_lat,
                           lead.primary_contact.other_lon,
                           lead.primary_contact.has_opted_out_of_email,
                           lead.primary_contact.has_opted_out_of_fax,
                           lead.primary_contact.do_not_call,
                           lead.primary_contact.birthday,
                           lead.lead_source.email]
                else:
                    row = [lead.id,
                           lead.title,
                           lead.get_status_display(),
                           str(len(lead.leadhistory_set.filter(created_at__gte=datetime.datetime.now()-datetime.timedelta(days=7)))),
                           str(len(lead.get_projects)),
                           '%s %s' % (lead.aac_poc.first_name, lead.aac_poc.last_name),
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           'n/a',
                           lead.lead_source.email]
                for tag in lead.tags.all():
                    row.append(tag)

                content.append(row)
        elif self.export_lead_list_general_tasks:
            headers = ['Lead ID', 'Lead', 'Lead Status', 'General Task ID', 'GT Status',
                'GT Priority', 'GT Due Date', 'GT Assignee', 'GT Description']
            content.append(headers)
            for gt in general_task_list:
                row = [ gt.lead.id,
                        gt.lead.title,
                        gt.lead.get_status_display(),
                        gt.form_id,
                        gt.status,
                        gt.get_priority_display(),
                        gt.requested_date,
                        str(gt.assignee),
                        gt.description ]
                content.append(row)

        return content

@cbv_decorator(permission_required('crm.view_lead'))
class ViewLead(DetailView):
    model = Lead
    pk_url_kwarg = 'lead_id'

    def get_context_data(self, **kwargs):
        context = super(ViewLead, self).get_context_data(**kwargs)
        context['add_lead_note_form'] = AddLeadNoteForm()
        context['open_general_task_count'] = \
            self.object.generaltask_set.filter(status__terminal=False).count()
        context['dv_count'] = \
            self.object.distinguishingvaluechallenge_set.all().count()
        context['opportunity_count'] = self.object.opportunity_set.all().count()

        return context

class ViewLeadGeneralInfo(ViewLead):
    template_name = 'timepiece/lead/view.html'

    def get_context_data(self, **kwargs):
        context = super(ViewLeadGeneralInfo, self).get_context_data(**kwargs)
        context['add_user_form'] = SelectContactForm()
        context['active'] = 'general_info'

        try:
            context['add_general_task_form'] = SelectGeneralTaskForm()
        except:
            pass

        return context

class ViewLeadDistinguishingValue(ViewLead):
    template_name = 'timepiece/lead/view_differentiating_value.html'

    def get_context_data(self, **kwargs):
        context = super(ViewLeadDistinguishingValue, self).get_context_data(**kwargs)
        context['active'] = 'distinguishing_value'

        if context['dv_count'] == 0:
            context['active_tab'] = 'empty'
        else:
            dvc_index = int(self.request.GET.get('tab', 1))
            context['active_tab'] = 'dvc%d' % (dvc_index)
            dvc_form = AddDistinguishingValueChallenegeForm()
            dvc = self.object.distinguishingvaluechallenge_set.all(
                )[dvc_index - 1]
            context['dvc_form'] = dvc_form
            context['dvc'] = dvc
        return context

class ViewLeadOpportunities(ViewLead):
    template_name = 'timepiece/lead/view_opportunities.html'

    def get_context_data(self, **kwargs):
        context = super(ViewLeadOpportunities, self).get_context_data(**kwargs)
        context['active'] = 'opportunities'

        return context

@cbv_decorator(permission_required('crm.add_leadnote'))
class AddLeadNote(View):

    def post(self, request, *args, **kwargs):
        user = self.request.user
        lead = Lead.objects.get(id=int(kwargs['lead_id']))
        note = LeadNote(lead=lead,
                           author=user,
                           text=request.POST.get('text', ''))
        if len(note.text):
            note.save()
        return HttpResponseRedirect(request.GET.get('next', None)
            or reverse('view_lead', args=(lead.id,)))

@cbv_decorator(permission_required('crm.add_leadnote'))
class LeadTags(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=200)

    def post(self, request, *args, **kwargs):
        lead = Lead.objects.get(id=int(kwargs['lead_id']))
        tag = request.POST.get('tag')
        for t in tag.split(','):
            if len(t):
                lead.tags.add(t)
        tags = [{'id': t.id,
                 'url': reverse('similar_items', args=(t.id,)),
                 'name':t.name} for t in lead.tags.all()]
        return HttpResponse(json.dumps({'tags': tags}),
                            content_type="application/json",
                            status=200)

@cbv_decorator(permission_required('crm.delete_lead'))
class RemoveLeadTag(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=501)

    def post(self, request, *args, **kwargs):
        # TODO: make this a permission
        if request.user.is_superuser or bool(len(request.user.groups.filter(id=8))):
            lead = Lead.objects.get(id=int(kwargs['lead_id']))
            tag = request.POST.get('tag')
            if len(tag):
                lead.tags.remove(tag)
        tags = [{'id': t.id,
                 'url': reverse('similar_items', args=(t.id,)),
                 'name':t.name} for t in lead.tags.all()]
        return HttpResponse(json.dumps({'tags': tags}),
                            content_type="application/json",
                            status=200)

@permission_required('crm.view_lead')
def lead_upload_attachment(request, lead_id):
    try:
        afu = AjaxFileUploader(MongoDBUploadBackend, db='lead_attachments')
        hr = afu(request)
        content = json.loads(hr.content)
        memo = {'uploader': str(request.user),
                'file_id': str(content['_id']),
                'upload_time': str(datetime.datetime.now()),
                'filename': content['filename']}
        memo.update(content)
        # save attachment to ticket
        attachment = LeadAttachment(
            lead=Lead.objects.get(id=int(lead_id)),
            file_id=str(content['_id']),
            filename=content['filename'],
            upload_time=datetime.datetime.now(),
            uploader=request.user,
            description='n/a')
        attachment.save()
        return HttpResponse(json.dumps(memo),
                            content_type="application/json")
    except:
        print sys.exc_info(), traceback.format_exc()
    return hr

@permission_required('crm.view_lead')
def lead_download_attachment(request, lead_id, attachment_id):
    MONGO_DB_INSTANCE = project_settings.MONGO_CLIENT.lead_attachments
    MONGO_DB_INSTANCE.authenticate(project_settings.MONGO_USER, project_settings.MONGO_PW)
    GRID_FS_INSTANCE = gridfs.GridFS(MONGO_DB_INSTANCE)
    try:
        lead_attachment = LeadAttachment.objects.get(
            lead__id=lead_id, id=attachment_id)
        f = GRID_FS_INSTANCE.get(ObjectId(lead_attachment.file_id))
        return HttpResponse(f.read(), content_type=f.content_type)
    except:
        return HttpResponse("Lead attachment could not be found.")

@cbv_decorator(permission_required('crm.add_lead'))
class CreateLead(CreateView):
    model = Lead
    form_class = CreateEditLeadForm
    template_name = 'timepiece/lead/create_edit.html'

    def get_initial(self):
        return {
            'lead_source': self.request.user,
            'aac_poc': self.request.user,
            'created_by': self.request.user,
            'last_editor': self.request.user,
        }

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.last_editor = self.request.user
        return super(CreateLead, self).form_valid(form)


@cbv_decorator(permission_required('crm.delete_lead'))
class DeleteLead(DeleteView):
    model = Lead
    success_url = reverse_lazy('list_leads')
    pk_url_kwarg = 'lead_id'
    template_name = 'timepiece/delete_object.html'


@cbv_decorator(permission_required('crm.change_lead'))
class EditLead(UpdateView):
    model = Lead
    form_class = CreateEditLeadForm
    template_name = 'timepiece/lead/create_edit.html'
    pk_url_kwarg = 'lead_id'


@cbv_decorator(permission_required('crm.change_lead'))
class AddLeadContact(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=501)

    def post(self, request, *args, **kwargs):
        try:
            lead = Lead.objects.get(id=int(kwargs['lead_id']))
            contact = SelectContactForm(request.POST).get_contact()
            if contact:
                lead.contacts.add(contact)
            return HttpResponseRedirect(request.GET.get('next', None)
                or reverse_lazy('view_lead', args=(lead.id,)))
        except:
            return HttpResponseRedirect(request.GET.get('next', None)
                or reverse_lazy('view_lead', args=(lead.id,)))

@cbv_decorator(permission_required('crm.change_lead'))
class RemoveLeadContact(View):

    def get(self, request, *args, **kwargs):
        lead = Lead.objects.get(id=int(kwargs['lead_id']))
        contact_id = request.GET.get('contact_id')
        contact = Contact.objects.get(id=int(contact_id))
        lead.contacts.remove(contact)
        return HttpResponseRedirect(request.GET.get('next', None)
            or reverse_lazy('view_lead', args=(lead.id,)))

@cbv_decorator(permission_required('crm.change_lead'))
class AddLeadGeneralTask(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=501)

    def post(self, request, *args, **kwargs):
        try:
            lead = Lead.objects.get(id=int(kwargs['lead_id']))
            general_task = SelectGeneralTaskForm(request.POST).get_general_task()
            if general_task.lead is None:
                general_task.lead = lead
                general_task.save()
            else:
                msg = '%s already belongs to Lead <a href="' + \
                reverse('view_lead', args=(general_task.lead.id,)) + \
                '">%s.  Please remove it from that Lead before ' + \
                'associating with this lead.' % (
                    general_task.form_id, general_task.lead.title)
                messages.error(request, msg)
        except:
            pass
        finally:
            return HttpResponseRedirect(request.GET.get('next', None)
                or reverse_lazy('view_lead', args=(lead.id,)))

@cbv_decorator(permission_required('crm.change_lead'))
class RemoveLeadGeneralTask(View):

    def get(self, request, *args, **kwargs):
        try:
            lead = Lead.objects.get(id=int(kwargs['lead_id']))
            general_task_id = request.GET.get('general_task_id')
            general_task = GeneralTask.objects.get(id=int(general_task_id))
            general_task.lead = None
            general_task.save()
        except:
            print sys.exc_info(), traceback.format_exc()
            pass
        finally:
            return HttpResponseRedirect(request.GET.get('next', None)
                or reverse_lazy('view_lead', args=(lead.id,)))


@cbv_decorator(permission_required('crm.add_distinguishingvaluechallenge'))
class AddDistinguishingValueChallenge(View):

    def get(self, request, *args, **kwargs):
        lead = Lead.objects.get(id=int(kwargs['lead_id']))
        dvc = DistinguishingValueChallenge(lead=lead)
        dvc.save()
        url = '%s?tab=%d' % (
            reverse('view_lead_distinguishing_value', args=(dvc.lead.id,)),
            list(dvc.lead.distinguishingvaluechallenge_set.all()
                ).index(dvc)+1)
        return HttpResponseRedirect(url)

@cbv_decorator(permission_required('crm.change_distinguishingvaluechallenge'))
class UpdateDistinguishingValueChallenge(View):

    def post(self, request, *args, **kwargs):

        dvc = DistinguishingValueChallenge.objects.get(id=int(request.POST.get('dvc', None)))
        dvc.probing_question = request.POST.get('probing_question', '')
        dvc.short_name = request.POST.get('short_name', '')
        dvc.description = request.POST.get('description', '')
        dvc.longevity = request.POST.get('longevity', '')
        if request.POST.get('start_date', None):
            try:
                start_date = datetime.datetime.strptime(
                    request.POST.get('start_date'), '%Y-%m-%d').date()
                dvc.start_date = start_date
            except:
                dvc.start_date = None
        else:
            dvc.start_date = None
        dvc.steps = request.POST.get('steps', '')
        dvc.results = request.POST.get('results', '')
        dvc.due = request.POST.get('due', '')
        if request.POST.get('due_date', None):
            try:
                due_date = datetime.datetime.strptime(
                    request.POST.get('due_date'), '%Y-%m-%d').date()
                dvc.due_date = due_date
            except:
                dvc.due_date = None
        else:
            dvc.due_date = None
        dvc.cost = request.POST.get('cost', '')

        dvc.confirm_resources = bool(request.POST.get('confirm_resources', False))
        dvc.resources_notes = request.POST.get('resources_notes', '')
        dvc.benefits_begin = request.POST.get('benefits_begin', '')
        if request.POST.get('date_benefits_begin', None):
            try:
                date_benefits_begin = datetime.datetime.strptime(
                    request.POST.get('date_benefits_begin'), '%Y-%m-%d').date()
                dvc.date_benefits_begin = date_benefits_begin
            except:
                dvc.date_benefits_begin = None
        else:
            dvc.date_benefits_begin = None
        dvc.confirm = bool(request.POST.get('confirm', False))
        dvc.confirm_notes = request.POST.get('confirm_notes', '')
        dvc.commitment = bool(request.POST.get('commitment', False))
        dvc.commitment_notes = request.POST.get('commitment_notes', '')

        dvc.closed = True if request.POST.get('closed', 'off') == 'on' else False
        dvc.save()

        try:
            order = int(request.POST.get('order', dvc.order))
            order = max(order, 1)
            if order != dvc.order:
                counter = 1
                for dvc2 in dvc.lead.distinguishingvaluechallenge_set.all():
                    if counter == order:
                        dvc.order = counter
                        dvc.save()
                        counter += 1
                    if dvc2 != dvc:
                        dvc2.order = counter
                        dvc2.save()
                        counter += 1
        except:
            pass

        url = '%s?tab=%d' % (
            reverse('view_lead_distinguishing_value', args=(dvc.lead.id,)),
            list(dvc.lead.distinguishingvaluechallenge_set.all()
                ).index(dvc)+1)
        return HttpResponseRedirect(url)

@cbv_decorator(permission_required('crm.delete_distinguishingvaluechallenge'))
class DeleteDistinguishingValueChallenge(DeleteView):
    model = DistinguishingValueChallenge
    pk_url_kwarg = 'dvc_id'
    template_name = 'timepiece/delete_object.html'

    def get_success_url(self):
        return reverse('view_lead_distinguishing_value',
            args=(int(self.kwargs['lead_id']),))

@cbv_decorator(permission_required('crm.add_distinguishingvaluechallenge'))
class AddTemplateDifferentiatingValues(FormView):
    form_class = AddTemplateDifferentiatingValuesForm
    template_name = 'timepiece/lead/add_template_differentiating_value.html'

    # def get_form(self, request):
    #     form = super(AddTemplateDifferentiatingValues, self).get_form(request)
    #     return form

    def form_valid(self, form):
        lead = Lead.objects.get(id=int(self.kwargs['lead_id']))
        for template_dv_id in form.cleaned_data['template_dvs']:
            template_dv = TemplateDifferentiatingValue.objects.get(
                id=int(template_dv_id))
            dv = DistinguishingValueChallenge(
                lead=lead,
                short_name=template_dv.short_name,
                probing_question=template_dv.probing_question)
            dv.save()

        return super(AddTemplateDifferentiatingValues, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(AddTemplateDifferentiatingValues, self).get_context_data(**kwargs)
        context['object'] = Lead.objects.get(id=int(self.kwargs.get('lead_id')))
        return context

    def get_success_url(self):
        return reverse('view_lead_distinguishing_value',
            args=(int(self.kwargs['lead_id']),))


@cbv_decorator(permission_required('auth.view_user'))
class ListTemplateDifferentiatingValue(SearchListView, CSVViewMixin):
    model = TemplateDifferentiatingValue
    search_fields = ['probing_question__icontains', 'short_name__icontains']
    template_name = 'timepiece/differentiating_value/list.html'

    def get(self, request, *args, **kwargs):
        self.export_template_dv_list = request.GET.get('export_template_dv_list', False)
        if self.export_template_dv_list:
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
            return super(ListTemplateDifferentiatingValue, self).get(request, *args, **kwargs)

    def get_filename(self, context):
        request = self.request.GET.copy()
        search = request.get('search', '(empty)')
        return 'template_dv_search_{0}'.format(search)

    def convert_context_to_csv(self, context):
        """Convert the context dictionary into a CSV file."""
        content = []
        dv_list = context['object_list']
        if self.export_template_dv_list:
            headers = ['Short Name', 'Probing Question']
            content.append(headers)
            for dv in dv_list:
                row = [dv.short_name, dv.probing_question]
                print 'row', row
                content.append(row)
        return content

@cbv_decorator(permission_required('crm.add_templatedifferentiatingvalue'))
class CreateTemplateDifferentiatingValue(CreateView):
    model = TemplateDifferentiatingValue
    form_class = CreateEditTemplateDVForm
    template_name = 'timepiece/differentiating_value/create_edit.html'

    def get_success_url(self):
        return reverse('list_template_differentiating_values')

@cbv_decorator(permission_required('crm.change_templatedifferentiatingvalue'))
class EditTemplateDifferentiatingValue(UpdateView):
    model = TemplateDifferentiatingValue
    pk_url_kwarg = 'template_dv_id'
    form_class = CreateEditTemplateDVForm
    template_name = 'timepiece/differentiating_value/create_edit.html'

    def get_success_url(self):
        return reverse('list_template_differentiating_values')

@cbv_decorator(permission_required('crm.delete_templatedifferentiatingvalue'))
class DeleteTemplateDifferentiatingValue(DeleteView):
    model = TemplateDifferentiatingValue
    pk_url_kwarg = 'template_dv_id'
    template_name = 'timepiece/delete_object.html'

    def get_success_url(self):
        return reverse('list_template_differentiating_values')

@cbv_decorator(permission_required('crm.add_templatedifferentiatingvalue'))
class CreateDVCostItem(CreateView):
    model = DVCostItem
    form_class = CreateEditDVCostItem
    template_name = 'timepiece/lead/cost_item/create_edit.html'

    def get_context_data(self, **kwargs):
        context = super(CreateDVCostItem, self).get_context_data(**kwargs)
        context['dv'] = DistinguishingValueChallenge.objects.get(
            id=int(self.kwargs['dvc_id']))
        return context

    def get_form(self, *args, **kwargs):
        form = super(CreateDVCostItem, self).get_form(*args, **kwargs)
        form.fields['dv'].widget = widgets.HiddenInput()
        form.fields['dv'].initial = DistinguishingValueChallenge.objects.get(
            id=int(self.kwargs['dvc_id']))
        return form

    def form_valid(self, form):
        form.instance.dv = DistinguishingValueChallenge.objects.get(
            id=int(self.kwargs['dvc_id']))
        return super(CreateDVCostItem, self).form_valid(form)

    def get_success_url(self):
        dvc = DistinguishingValueChallenge.objects.get(id=int(self.kwargs['dvc_id']))
        return '%s?tab=%d#cost' % (
            reverse('view_lead_distinguishing_value', args=(dvc.lead.id,)),
            list(dvc.lead.distinguishingvaluechallenge_set.all()
                ).index(dvc)+1)

@cbv_decorator(permission_required('crm.change_templatedifferentiatingvalue'))
class EditDVCostItem(UpdateView):
    model = DVCostItem
    pk_url_kwarg = 'cost_item_id'
    form_class = CreateEditDVCostItem
    template_name = 'timepiece/lead/cost_item/create_edit.html'

    def get_context_data(self, **kwargs):
        context = super(EditDVCostItem, self).get_context_data(**kwargs)
        context['dv'] = DistinguishingValueChallenge.objects.get(
            id=int(self.kwargs['dvc_id']))
        return context

    def get_form(self, *args, **kwargs):
        form = super(EditDVCostItem, self).get_form(*args, **kwargs)
        form.fields['dv'].widget = widgets.HiddenInput()
        form.fields['dv'].initial = DistinguishingValueChallenge.objects.get(
            id=int(self.kwargs['dvc_id']))
        return form

    def form_valid(self, form):
        form.instance.dv = DistinguishingValueChallenge.objects.get(
            id=int(self.kwargs['dvc_id']))
        return super(EditDVCostItem, self).form_valid(form)

    def get_success_url(self):
        dvc = DistinguishingValueChallenge.objects.get(id=int(self.kwargs['dvc_id']))
        return '%s?tab=%d#cost' % (
            reverse('view_lead_distinguishing_value', args=(dvc.lead.id,)),
            list(dvc.lead.distinguishingvaluechallenge_set.all()
                ).index(dvc)+1)

@cbv_decorator(permission_required('crm.delete_templatedifferentiatingvalue'))
class DeleteDVCostItem(DeleteView):
    model = DVCostItem
    pk_url_kwarg = 'cost_item_id'
    template_name = 'timepiece/delete_object.html'

    def get_success_url(self):
        dvc = DistinguishingValueChallenge.objects.get(id=int(self.kwargs['dvc_id']))
        return '%s?tab=%d#cost' % (
            reverse('view_lead_distinguishing_value', args=(dvc.lead.id,)),
            list(dvc.lead.distinguishingvaluechallenge_set.all()
                ).index(dvc)+1)

@cbv_decorator(permission_required('crm.add_opportunity'))
class CreateOpportunity(CreateView):
    model = Opportunity
    pk_url_kwarg = 'opportunity_id'
    form_class = CreateEditOpportunity
    template_name = 'timepiece/lead/opportunity/create_edit.html'

    def get_success_url(self):
        return reverse('view_lead_opportunities', args=(int(self.kwargs['lead_id']), ))

    def get_form(self, *args, **kwargs):
        form = super(CreateOpportunity, self).get_form(*args, **kwargs)
        form.fields['proposal'].queryset = LeadAttachment.objects.filter(
            lead__id=int(self.kwargs['lead_id']))
        form.fields['differentiating_value'].queryset = \
            DistinguishingValueChallenge.objects.filter(
            lead__id=int(self.kwargs['lead_id']))
        return form

    def get_context_data(self, **kwargs):
        context = super(CreateOpportunity, self).get_context_data(**kwargs)
        context['lead'] = Lead.objects.get(id=int(self.kwargs['lead_id']))
        return context

    def get_initial(self):
        return {
            'lead': self.kwargs['lead_id'],
            'differentiating_value': self.request.GET.get(
                'differentiating_value', None),
        }

    def form_valid(self, form):
        # form.instance.created_by = self.request.user
        # form.instance.last_editor = self.request.user
        return super(CreateOpportunity, self).form_valid(form)

@cbv_decorator(permission_required('crm.change_opportunity'))
class EditOpportunity(UpdateView):
    model = Opportunity
    pk_url_kwarg = 'opportunity_id'
    form_class = CreateEditOpportunity
    template_name = 'timepiece/lead/create_edit.html'

    def get_form(self, *args, **kwargs):
        form = super(EditOpportunity, self).get_form(*args, **kwargs)
        form.fields['proposal'].queryset = LeadAttachment.objects.filter(
            lead__id=int(self.kwargs['lead_id']))
        form.fields['differentiating_value'].queryset = \
            DistinguishingValueChallenge.objects.filter(
            lead__id=int(self.kwargs['lead_id']))
        return form

    def get_context_data(self, **kwargs):
        context = super(EditOpportunity, self).get_context_data(**kwargs)
        context['lead'] = Lead.objects.get(id=int(self.kwargs['lead_id']))
        return context

    def form_valid(self, form):
        # form.instance.last_editor = self.request.user
        return super(EditOpportunity, self).form_valid(form)

    def get_success_url(self):
        return reverse('view_lead_opportunities',
            args=(int(self.kwargs['lead_id']),))

@cbv_decorator(permission_required('crm.delete_opportunity'))
class DeleteOpportunity(DeleteView):
    model = Opportunity
    pk_url_kwarg = 'opportunity_id'
    template_name = 'timepiece/delete_object.html'

    def get_success_url(self):
        return reverse('view_lead_opportunities',
            args=(int(self.kwargs['lead_id']),))


@csrf_exempt
# @permission_required('project.add_projectattachment')
def project_s3_attachment(request, project_id):
    bucket = request.POST.get('bucket', None)
    uuid = request.POST.get('key', None)
    userid = int(request.POST.get('firmbase-userid', 4))
    filename = request.POST.get('name', '')

    attachment = ProjectAttachment(
        project=Project.objects.get(id=int(project_id)),
        bucket=bucket,
        uuid=uuid,
        filename=filename,
        uploader=User.objects.get(id=userid))
    attachment.save()

    return HttpResponse(status=200)

@permission_required('crm.view_projectattachment')
def project_download_attachment(request, project_id, attachment_id):
    try:
        project_attachment = ProjectAttachment.objects.get(
            project_id=project_id, id=attachment_id)
        return HttpResponseRedirect(project_attachment.get_download_url())
    except:
        return HttpResponse('Project attachment could not be found.')
