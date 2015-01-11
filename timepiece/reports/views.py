import csv
from dateutil.relativedelta import relativedelta
from itertools import groupby
import json
import pprint
pp = pprint.PrettyPrinter(indent=4)

from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Sum, Q, Min, Max
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.defaultfilters import date as date_format_filter
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from timepiece import utils
from timepiece.utils.csv import CSVViewMixin, DecimalEncoder

from timepiece.contracts.models import ProjectContract
from timepiece.entries.models import Entry, ProjectHours
from timepiece.crm.models import Project
from timepiece.reports.forms import BillableHoursReportForm, HourlyReportForm,\
        ProductivityReportForm, PayrollSummaryReportForm
from timepiece.reports.utils import get_project_totals, get_payroll_totals,\
        generate_dates, get_week_window

from timepiece.reports.utils import get_week_trunc_sunday, multikeysort


class ReportMixin(object):
    """Common data for the Hourly & Billable Hours reports."""

    @method_decorator(permission_required('entries.view_entry_summary'))
    def dispatch(self, request, *args, **kwargs):
        return super(ReportMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Processes form data to get relevant entries & date_headers."""
        context = super(ReportMixin, self).get_context_data(**kwargs)

        form = self.get_form()
        if form.is_valid():
            data = form.cleaned_data
            start, end = form.save()
            entryQ = self.get_entry_query(start, end, data)
            trunc = data['trunc']
            if entryQ:
                vals = ('pk', 'activity', 'activity__name', 'project', 'project__code',
                        'project__name', 'project__status', 'project__type__label', 
                        'user__email', 'project__business__id', 'project__business__name',
                        'comments', 'writedown')
                # EXTRA LOGIC FOR SUN-SAT WEEK
                if trunc == 'week':
                    entries = Entry.objects.date_trunc('day',
                            extra_values=vals).filter(entryQ)
                    entries = list(entries)
                    for i in range(len(entries)):
                        entries[i]['date'] = get_week_trunc_sunday(entries[i]['date'])
                else:
                    entries = Entry.objects.date_trunc(trunc,
                            extra_values=vals).filter(entryQ)
            else:
                entries = Entry.objects.none()

            end = end - relativedelta(days=1)
            date_headers = generate_dates(start, end, by=trunc)
            context.update({
                'from_date': start,
                'to_date': end,
                'date_headers': date_headers,
                'entries': entries,
                'filter_form': form,
                'trunc': trunc,
            })
        else:
            context.update({
                'from_date': None,
                'to_date': None,
                'date_headers': [],
                'entries': Entry.objects.none(),
                'filter_form': form,
                'trunc': '',
            })

        return context

    def get_entry_query(self, start, end, data):
        """Builds Entry query from form data."""
        # Entry types.
        incl_billable = data.get('billable', True)
        incl_nonbillable = data.get('non_billable', True)
        incl_writedown = data.get('writedown', True)
        incl_leave = data.get('paid_time_off', True)
        incl_unpaid = data.get('unpaid_time_off', True)

        # If no types are selected, shortcut & return nothing.
        if not any((incl_billable, incl_nonbillable, incl_writedown, incl_leave, incl_unpaid)):
            return None

        # All entries must meet time period requirements.
        basicQ = Q(end_time__gte=start, end_time__lt=end)

        # Filter by project for HourlyReport.
        projects = data.get('projects', None)
        businesses = data.get('businesses', None)
        basicQ &= Q(project__in=projects) if projects else Q()
        basicQ &= Q(project__business__in=businesses) if businesses else Q()

        # Filter by user, activity, and project type for BillableReport.
        if 'users' in data:
            basicQ &= Q(user__in=data.get('users'))
        if 'activities' in data:
            basicQ &= Q(activity__in=data.get('activities'))
        if 'project_types' in data:
            basicQ &= Q(project__type__in=data.get('project_types'))
        
        # if we do not want to include writedown, set that here.
        if not incl_writedown:
            basicQ &= Q(writedown=False)

        # If all types are selected, no further filtering is required.
        if all((incl_billable, incl_nonbillable, incl_leave, incl_unpaid)):
            return basicQ
        
        # If all but unpaid types are selected, little filtering is required.
        unpaid_ids = utils.get_setting('TIMEPIECE_UNPAID_LEAVE_PROJECTS').values()
        unpaidQ = Q(project__in=unpaid_ids)
        if all((incl_billable, incl_nonbillable, incl_leave)):
            return basicQ & ~unpaidQ

        # Filter by whether a project is billable or non-billable.
        billableQ = None
        if incl_billable and not incl_nonbillable:
            billableQ = Q(activity__billable=True,
                    project__type__billable=True)
        if incl_nonbillable and not incl_billable:
            billableQ = Q(activity__billable=False) |\
                    Q(project__type__billable=False)

        # Filter by whether the entry is paid leave.
        leave_ids = utils.get_setting('TIMEPIECE_PAID_LEAVE_PROJECTS').values()
        leaveQ = Q(project__in=leave_ids)
        if incl_leave:
            extraQ = (leaveQ | billableQ) if billableQ else leaveQ
        else:
            extraQ = (~leaveQ & billableQ) if billableQ else ~leaveQ

        if incl_unpaid:
            extraQ = (extraQ | unpaidQ) if billableQ or incl_leave else unpaidQ
        else:
            extraQ &= ~unpaidQ
        
        return basicQ & extraQ

    def get_headers(self, date_headers, from_date, to_date, trunc):
        """Adjust date headers & get range headers."""
        date_headers = list(date_headers)

        # Earliest date should be no earlier than from_date.
        if date_headers and date_headers[0] < from_date:
            date_headers[0] = from_date

        # When organizing by week or month, create a list of the range for
        # each date header.
        if date_headers and trunc != 'day':
            count = len(date_headers)
            range_headers = [0] * count
            for i in range(count - 1):
                range_headers[i] = (date_headers[i], date_headers[i + 1] -
                        relativedelta(days=1))
            range_headers[count - 1] = (date_headers[count - 1], to_date)
        else:
            range_headers = date_headers
        return date_headers, range_headers

    def get_previous_month(self):
        """Returns date range for the previous full month."""
        end = utils.get_month_start() - relativedelta(days=1)
        end = utils.to_datetime(end)
        start = utils.get_month_start(end)
        return start, end


class HourlyReport(ReportMixin, CSVViewMixin, TemplateView):
    template_name = 'timepiece/reports/hourly.html'

    def convert_context_to_csv(self, context):
        """Convert the context dictionary into a CSV file."""
        content = []
        if self.export_users_details:
            # this is a special csv export, different than stock Timepiece,
            # requested by AAC Engineering for their detailed reporting reqs
            headers = ['Entry ID', 'Date', 'Employee ID', 'Employee Email',
                       'Employee Last Name', 'Employee First Name', 'Project ID', 'Project Code',
                       'Project Name', 'Project Type', 'Business ID', 'Business Name',
                       'Duration', 'Activity ID', 'Activity Name', 'Comment']
            content.append(headers)
            for entry in context['entries']:
                row = [entry['pk']]
                row.append(entry['date'].strftime('%m/%d/%Y'))
                for key in ['user', 'user__email', 'user__last_name', 'user__first_name',
                          'project', 'project__code', 'project__name', 'project__type__label',
                          'project__business__id', 'project__business__name',
                          'hours', 'activity', 'activity__name', 'comments']:
                    row.append(entry[key])
                content.append(row)
            return content

        date_headers = context['date_headers']

        headers = ['Name']
        headers.extend([date.strftime('%m/%d/%Y') for date in date_headers])
        headers.append('Total')
        content.append(headers)
        
        if self.export_projects:
            key = 'By Project (All Projects)'
        elif self.export_users:
            key = 'By User'

        summaries = context['summaries']
        try:
            summary = filter(lambda x:x[0]==key, summaries)[0][1]
        except:
            summary = []
        for rows, totals in summary:
            for name, user_id, hours in rows:
                data = [name]
                data.extend(hours)
                content.append(data)
            total = ['Totals']
            total.extend(totals)
            content.append(total)
        return content

    @property
    def defaults(self):
        """Default filter form data when no GET data is provided."""
        # Set default date span to previous week.
        (start, end) = get_week_window(timezone.now() - relativedelta(days=7))
        return {
            'from_date': start,
            'to_date': end,
            'billable': True,
            'non_billable': False,
            'paid_time_off': False,
            'unpaid_time_off': False,
            'writedown': True,
            'trunc': 'day',
            'projects': [],
            'businesses': [],
        }

    def get(self, request, *args, **kwargs):
        self.export_users = request.GET.get('export_users', False)
        self.export_projects = request.GET.get('export_projects', False)
        self.export_users_details = request.GET.get('export_users_details', False)
        
        context = self.get_context_data()
        if self.export_users or self.export_projects or self.export_users_details:
            kls = CSVViewMixin
        else:
            kls = TemplateView
        return kls.render_to_response(self, context)

    def get_context_data(self, **kwargs):
        context = super(HourlyReport, self).get_context_data(**kwargs)

        # Sum the hours totals for each user & interval.
        entries = context['entries']
        date_headers = context['date_headers']

        summaries = []
        if context['entries']:
            entries_is_list = type(entries) is list
            # print 'ENTRIES', entries
            if entries_is_list:
                ordered_entries = multikeysort(entries, ['user__last_name', 'user', 'date'])
            else:
                ordered_entries = entries.order_by('user__last_name', 'user__id', 'date')
            summaries.append(('By User', get_project_totals(ordered_entries,
                    date_headers, 'total', total_column=True, by='user')))

            if entries_is_list:
                ordered_entries = multikeysort(entries, ['project__type__label', 'project__name',
                    'project__code', 'date'])
            else:
                ordered_entries = entries.order_by('project__type__label', 'project__name',
                    'project__code', 'date')
            
            summaries.append(('By Project (All Projects)', get_project_totals(
                ordered_entries, date_headers, 'total', total_column=True, by='project')))
            func = lambda x: x['project__type__label']
            for label, group in groupby(ordered_entries, func):
                title = 'By Project (' + label + ' Projects)'
                summaries.append((title, get_project_totals(list(group),
                        date_headers, 'total', total_column=True, by='project')))

            summaries.append(('Writedowns By Project (All Projects)', get_project_totals(
                ordered_entries, date_headers, 'total', total_column=True, by='project', writedown=True)))
            

        # Adjust date headers & create range headers.
        from_date = context['from_date']
        from_date = utils.add_timezone(from_date) if from_date else None
        to_date = context['to_date']
        to_date = utils.add_timezone(to_date) if to_date else None
        trunc = context['trunc']
        date_headers, range_headers = self.get_headers(date_headers,
                from_date, to_date, trunc)

        context.update({
            'date_headers': date_headers,
            'summaries': summaries,
            'range_headers': range_headers,
        })
        return context

    def get_filename(self, context):
        request = self.request.GET.copy()
        from_date = request.get('from_date')
        to_date = request.get('to_date')
        return 'hours_{0}_to_{1}_by_{2}.csv'.format(from_date, to_date,
            context.get('trunc', ''))

    def get_form(self):
        data = self.request.GET or self.defaults
        data = data.copy()  # make mutable
        # Fix booleans - the strings "0" and "false" are True in Python
        for key in ['billable', 'non_billable', 'paid_time_off', 'unpaid_time_off', 'writedown']:
            data[key] = key in data and \
                        str(data[key]).lower() in ('on', 'true', '1')

        return HourlyReportForm(data)


class WritedownReport(ReportMixin, CSVViewMixin, TemplateView):
    template_name = 'timepiece/reports/writedowns.html'

    def convert_context_to_csv(self, context):
        """Convert the context dictionary into a CSV file."""
        content = []
        if self.export_users_details:
            # this is a special csv export, different than stock Timepiece,
            # requested by AAC Engineering for their detailed reporting reqs
            headers = ['Entry ID', 'Date', 'Employee ID', 'Employee Email',
                       'Employee Last Name', 'Employee First Name', 'Project ID', 'Project Code',
                       'Project Name', 'Project Type', 'Business ID', 'Business Name',
                       'Duration', 'Activity ID', 'Activity Name', 'Comment']
            content.append(headers)
            for entry in context['entries']:
                row = [entry['pk']]
                row.append(entry['date'].strftime('%m/%d/%Y'))
                for key in ['user', 'user__email', 'user__last_name', 'user__first_name',
                          'project', 'project__code', 'project__name', 'project__type__label',
                          'project__business__id', 'project__business__name',
                          'hours', 'activity', 'activity__name', 'comments']:
                    row.append(entry[key])
                content.append(row)
            return content

        date_headers = context['date_headers']

        headers = ['Name']
        headers.extend([date.strftime('%m/%d/%Y') for date in date_headers])
        headers.append('Total')
        content.append(headers)
        
        if self.export_projects:
            key = 'By Project (All Projects)'
        elif self.export_users:
            key = 'By User'

        summaries = context['summaries']
        try:
            summary = filter(lambda x:x[0]==key, summaries)[0][1]
        except:
            summary = []
        for rows, totals in summary:
            for name, user_id, hours in rows:
                data = [name]
                data.extend(hours)
                content.append(data)
            total = ['Totals']
            total.extend(totals)
            content.append(total)
        return content

    @property
    def defaults(self):
        """Default filter form data when no GET data is provided."""
        # Set default date span to previous week.
        (start, end) = get_week_window(timezone.now() - relativedelta(days=7))
        return {
            'from_date': start,
            'to_date': end,
            'billable': True,
            'non_billable': False,
            'paid_time_off': False,
            'writedown': True,
            'trunc': 'day',
            'projects': [],
            'businesses': [],
        }

    def get(self, request, *args, **kwargs):
        self.export_users = request.GET.get('export_users', False)
        self.export_projects = request.GET.get('export_projects', False)
        self.export_users_details = request.GET.get('export_users_details', False)
        
        context = self.get_context_data()
        if self.export_users or self.export_projects or self.export_users_details:
            kls = CSVViewMixin
        else:
            kls = TemplateView
        return kls.render_to_response(self, context)

    def get_context_data(self, **kwargs):
        context = super(WritedownReport, self).get_context_data(**kwargs)

        # Sum the hours totals for each user & interval.
        entries = context['entries']
        entries = entries.filter(writedown=True)
        context['entries'] = entries
        date_headers = context['date_headers']

        summaries = []
        if context['entries']:
            entries_is_list = type(entries) is list
            if entries_is_list:
                ordered_entries = multikeysort(entries, ['user__last_name', 'user', 'date'])
            else:
                ordered_entries = entries.order_by('user__last_name', 'user__id', 'date')
            summaries.append(('By User', get_project_totals(ordered_entries,
                    date_headers, 'total', total_column=True, by='user')))

            if entries_is_list:
                ordered_entries = multikeysort(entries, ['project__type__label', 'project__name',
                    'project__code', 'date'])
            else:
                ordered_entries = entries.order_by('project__type__label', 'project__name',
                    'project__code', 'date')
            
            summaries.append(('By Project (All Projects)', get_project_totals(
                ordered_entries, date_headers, 'total', total_column=True, by='project')))
            

        # Adjust date headers & create range headers.
        from_date = context['from_date']
        from_date = utils.add_timezone(from_date) if from_date else None
        to_date = context['to_date']
        to_date = utils.add_timezone(to_date) if to_date else None
        trunc = context['trunc']
        date_headers, range_headers = self.get_headers(date_headers,
                from_date, to_date, trunc)

        context.update({
            'date_headers': date_headers,
            'summaries': summaries,
            'range_headers': range_headers,
        })
        return context

    def get_filename(self, context):
        request = self.request.GET.copy()
        from_date = request.get('from_date')
        to_date = request.get('to_date')
        return 'writedowns_{0}_to_{1}_by_{2}.csv'.format(from_date, to_date,
            context.get('trunc', ''))

    def get_form(self):
        data = self.request.GET or self.defaults
        data = data.copy()  # make mutable
        # Fix booleans - the strings "0" and "false" are True in Python
        for key in ['billable', 'non_billable', 'paid_time_off', 'writedown']:
            data[key] = key in data and \
                        str(data[key]).lower() in ('on', 'true', '1')

        return HourlyReportForm(data)

class BillableHours(ReportMixin, TemplateView):
    template_name = 'timepiece/reports/billable_hours.html'

    @property
    def defaults(self):
        """Default filter form data when no GET data is provided."""
        start, end = self.get_previous_month()
        return {
            'from_date': start,
            'to_date': end,
            'trunc': 'week',
        }

    def get_context_data(self, **kwargs):
        context = super(BillableHours, self).get_context_data(**kwargs)

        entries = context['entries']
        date_headers = context['date_headers']
        data_map = self.get_hours_data(entries, date_headers)

        from_date = context['from_date']
        to_date = context['to_date']
        trunc = context['trunc']
        kwargs = {trunc + 's': 1}  # For relativedelta

        keys = sorted(data_map.keys())
        data_list = [['Date', 'Billable', 'Non-billable']]
        for i in range(len(keys)):
            start = keys[i]
            start = start if start >= from_date else from_date
            end = start + relativedelta(**kwargs) - relativedelta(days=1)
            end = end if end <= to_date else to_date

            if start != end:
                label = ' - '.join([date_format_filter(d, 'M j') for d in (start, end)])
            else:
                label = date_format_filter(start, 'M j')
            billable = data_map[keys[i]]['billable']
            nonbillable = data_map[keys[i]]['nonbillable']
            data_list.append([label, billable, nonbillable])

        context.update({
            'data': json.dumps(data_list, cls=DecimalEncoder),
        })
        return context

    def get_form(self):
        if self.request.GET:
            return BillableHoursReportForm(self.request.GET)
        else:
            # Select all available users, activities, and project types.
            return BillableHoursReportForm(self.defaults,
                    select_all=True)

    def get_hours_data(self, entries, date_headers):
        """
        Sum billable and non-billable hours across all users.
        Seprate writedowns so that they can be moved from billable
        into non-billable.
        """
        writedowns_only = [e for e in entries if e['writedown']]
        print 'writedowns_only', writedowns_only
        project_totals = get_project_totals(entries, date_headers, 
            total_column=False) if entries else []
        project_writedown_totals = get_project_totals(writedowns_only,
            date_headers, total_column=False
            ) if writedowns_only else []

        data_map = {}
        # first, get standard project totals data
        for rows, totals in project_totals:
            for user, user_id, periods in rows:
                for period in periods:
                    day = period['day']
                    if day not in data_map:
                        data_map[day] = {'billable': 0, 'nonbillable': 0}
                    data_map[day]['billable'] += period['billable']
                    data_map[day]['nonbillable'] += period['nonbillable']

        # then, add writedown entries that were not included in the above
        # filtered entries to the non-billable totals
        for rows, totals in project_writedown_totals:
            for user, user_id, periods in rows:
                for period in periods:
                    day = period['day']
                    if day not in data_map:
                        data_map[day] = {'billable': 0, 'nonbillable': 0}
                    data_map[day]['nonbillable'] -= period['billable']
                    assert(period['nonbillable']==0)
        return data_map


@permission_required('entries.view_payroll_summary')
def report_payroll_summary(request):
    # date = timezone.now() - relativedelta(months=1)
    # from_date = utils.get_month_start(date).date()
    # to_date = from_date + relativedelta(months=1)
    (from_date, to_date) = utils.get_bimonthly_dates(timezone.now())
    (from_date, to_date) = utils.get_bimonthly_dates(from_date - relativedelta(days=1))

    year_month_form = PayrollSummaryReportForm(request.GET or None,
        initial={'month': from_date.month, 'year': from_date.year, 'half':1 if from_date.day <= 15 else 2})

    if year_month_form.is_valid():
        from_date, to_date = year_month_form.save()
    last_billable = utils.get_last_billable_day(from_date)
    projects = utils.get_setting('TIMEPIECE_PAID_LEAVE_PROJECTS')
    unpaid_projects = utils.get_setting('TIMEPIECE_UNPAID_LEAVE_PROJECTS')
    writedownQ = Q(writedown=False)
    weekQ = Q(end_time__gt=from_date, #utils.get_week_start(from_date),
              end_time__lt=to_date) # CHANGED FOR AAC last_billable + relativedelta(days=1))
    monthQ = Q(end_time__gt=from_date, end_time__lt=to_date)
    workQ = ~Q(project__in=projects.values())
    unpaidQ = ~Q(project__in=unpaid_projects.values())
    statusQ = Q(status=Entry.INVOICED) | Q(status=Entry.APPROVED)
    # Weekly totals
    if utils.get_setting('TIMEPIECE_WEEK_START', default=0) == 0:
        week_entries = Entry.objects.date_trunc('week').filter(
            writedownQ, weekQ, statusQ, workQ, unpaidQ
        ).order_by('user')
    else:
        week_entries = []
        for we in Entry.objects.filter(writedownQ, weekQ, statusQ, workQ, unpaidQ).order_by('user'):
            week_entries.append(
                {'billable': we.billable,
                 'date': utils.get_week_start(we.end_time).date(),
                 'hours': we.hours,
                 'user': we.user.id,
                 'user__first_name': we.user.first_name,
                 'user__last_name': we.user.last_name}
            )
        week_entries = sorted(week_entries, key=lambda x:x['user__last_name'])

    #date_headers = generate_dates(from_date, last_billable, by='week')
    date_headers = generate_dates(from_date, to_date, by='week')
    weekly_totals = list(get_project_totals(week_entries, date_headers,
                                              'total', overtime=True))
    # Monthly totals
    # not filter on writedown here since there should never be a writedown
    # against a PAID LEAVE project.
    leave = Entry.objects.filter(monthQ, ~workQ
                                  ).values('user', 'hours', 'project__name')
    extra_values = ('project__type__label',)
    month_entries = Entry.objects.date_trunc('month', extra_values)
    month_entries_valid = month_entries.filter(monthQ, statusQ, workQ, unpaidQ)
    labels, monthly_totals = get_payroll_totals(month_entries_valid, leave)
    # Unapproved and unverified hours
    entries = Entry.objects.filter(writedownQ, monthQ).order_by()  # No ordering
    user_values = ['user__pk', 'user__first_name', 'user__last_name']
    unverified = entries.filter(status=Entry.UNVERIFIED #, user__is_active=True) \
                        ).values_list(*user_values).distinct()
    unapproved = entries.filter(status=Entry.VERIFIED) \
                        .values_list(*user_values).distinct()
    to_date_link = to_date - relativedelta(days=1)
    return render(request, 'timepiece/reports/payroll_summary.html', {
        'from_date': from_date,
        'to_date': to_date_link,
        'year_month_form': year_month_form,
        'date_headers': date_headers,
        'weekly_totals': weekly_totals,
        'monthly_totals': monthly_totals,
        'unverified': unverified,
        'unapproved': unapproved,
        'labels': labels,
    })


@permission_required('entries.view_entry_summary')
def report_productivity(request):
    report = []
    organize_by = None

    form = ProductivityReportForm(request.GET or None)
    if form.is_valid():
        project = form.cleaned_data['project']
        organize_by = form.cleaned_data['organize_by']
        export = request.GET.get('export', False)

        actualsQ = Q(project=project, end_time__isnull=False)
        actuals = Entry.objects.filter(actualsQ)
        projections = ProjectHours.objects.filter(project=project)
        entry_count = actuals.count() + projections.count()

        if organize_by == 'week' and entry_count > 0:
            # Determine the project's time range.
            amin, amax, pmin, pmax = (None, None, None, None)
            if actuals.count() > 0:
                amin = actuals.aggregate(Min('start_time')).values()[0]
                amin = utils.get_week_start(amin).date()
                amax = actuals.aggregate(Max('start_time')).values()[0]
                amax = utils.get_week_start(amax).date()
            if projections.count() > 0:
                pmin = projections.aggregate(Min('week_start')).values()[0]
                pmax = projections.aggregate(Max('week_start')).values()[0]
            current = min(amin, pmin) if (amin and pmin) else (amin or pmin)
            latest = max(amax, pmax) if (amax and pmax) else (amax or pmax)

            # Report for each week during the project's time range.
            while current <= latest:
                next_week = current + relativedelta(days=7)
                actual_hours = actuals.filter(start_time__gte=current,
                        start_time__lt=next_week).aggregate(
                        Sum('hours')).values()[0]
                projected_hours = projections.filter(week_start__gte=current,
                        week_start__lt=next_week).aggregate(
                        Sum('hours')).values()[0]
                report.append([date_format_filter(current, 'M j, Y'),
                        actual_hours or 0, projected_hours or 0])
                current = next_week

        elif organize_by == 'user' and entry_count > 0:
            # Determine all users who worked on or were assigned to the
            # project.
            vals = ('user', 'user__first_name', 'user__last_name')
            ausers = list(actuals.values_list(*vals).distinct())
            pusers = list(projections.values_list(*vals).distinct())
            key = lambda x: (x[1] + x[2]).lower()  # Sort by name
            users = sorted(list(set(ausers + pusers)), key=key)

            # Report for each user.
            for user in users:
                name = '{0} {1}'.format(user[1], user[2])
                actual_hours = actuals.filter(user=user[0]) \
                        .aggregate(Sum('hours')).values()[0]
                projected_hours = projections.filter(user=user[0]) \
                        .aggregate(Sum('hours')).values()[0]
                report.append([name, actual_hours or 0, projected_hours or 0])

        col_headers = [organize_by.title(), 'Worked Hours', 'Assigned Hours']
        report.insert(0, col_headers)

        if export:
            response = HttpResponse(content_type='text/csv')
            filename = '{0}_productivity'.format(project.name)
            content_disp = 'attachment; filename={0}.csv'.format(filename)
            response['Content-Disposition'] = content_disp
            writer = csv.writer(response)
            for row in report:
                writer.writerow(row)
            return response

    return render(request, 'timepiece/reports/productivity.html', {
        'form': form,
        'report': json.dumps(report, cls=DecimalEncoder),
        'type': organize_by or '',
        'total_worked': sum([r[1] for r in report[1:]]),
        'total_assigned': sum([r[2] for r in report[1:]]),
    })

@permission_required('contracts.view_estimation_accuracy')
def report_estimation_accuracy(request):
    """
    Idea from Software Estimation, Demystifying the Black Art, McConnel 2006 Fig 3-3.
    """
    contracts = ProjectContract.objects.filter(
        status=ProjectContract.STATUS_COMPLETE,
        type=ProjectContract.PROJECT_FIXED
    )
    data = [('Target (hrs)', 'Actual (hrs)', 'Point Label')]
    for c in contracts:
        if c.contracted_hours() == 0:
            continue
        pt_label = "%s (%.2f%%)" % (c.name, 
                                    c.hours_worked / c.contracted_hours() * 100)
        data.append((c.contracted_hours(), c.hours_worked, pt_label))
        chart_max = max([max(x[0], x[1]) for x in data[1:]]) #max of all targets & actuals
    return render(request, 'timepiece/reports/estimation_accuracy.html', {
        'data': json.dumps(data, cls=DecimalEncoder),
        'chart_max': chart_max,
    })


from django.contrib.auth.models import Group
from timepiece.crm.models import ActivityGoal, Project
from django.db.models import Sum, Q
@permission_required('crm.view_employee_backlog')
def report_backlog(request):
    """
    Determines company-wide backlog and displays
    """
    if request.user.has_perm('crm.view_backlog'):
        backlog = {}
        for employee in Group.objects.get(id=1).user_set.filter(is_active=True).order_by('last_name', 'first_name'):
            backlog[employee.id] =[]
            for employee, activity_goals in groupby(ActivityGoal.objects.filter(employee=employee, milestone__project__status=4).order_by('activity'), lambda x: x.employee):
                for activity, activity_goals in groupby(activity_goals, lambda x: x.activity):
                    activity_hours = 0.0
                    charged_hours = 0.0
                    #print 'employee', employee.first_name, employee.last_name, 'activity', activity
                    if activity is None:
                        activity_name = 'Other'
                        for activity_goal in activity_goals:
                            if activity_goal.date and ActivityGoal.objects.filter(employee=employee, milestone=activity_goal.milestone, date__gt=activity_goal.date, activity=activity).count():
                                # only get the latest date for this combo
                                continue
                            activity_hours += float(activity_goal.goal_hours)
                            charged_hours += float(Entry.objects.filter(project=activity_goal.milestone.project, user=employee
                                ).exclude(Q(activity__id=12)|Q(activity__id=17)|Q(activity__id=11)
                                ).aggregate(Sum('hours'))['hours__sum'] or 0.0)
                    else:
                        activity_name = activity.name
                        for activity_goal in activity_goals:
                            if activity_goal.date and ActivityGoal.objects.filter(employee=employee, 
                                milestone=activity_goal.milestone, 
                                date__gt=activity_goal.date, 
                                activity=activity).count():
                                # only get the latest date for this combo
                                continue
                            activity_hours += float(activity_goal.goal_hours)
                            charged_hours += float(Entry.objects.filter(project=activity_goal.milestone.project,
                                                                        activity=activity,
                                                                        user=employee
                                                                        ).aggregate(Sum('hours'))['hours__sum'] or 0.0)
                    percentage = 100.*(float(charged_hours)/float(activity_hours)) if float(activity_hours) > 0 else 0
                    percentage = 100 if float(activity_hours)==0.0 else percentage
                    backlog[employee.id].append({'activity': activity,
                                                 'activity_name': activity_name,
                                                 'employee': employee,
                                                 'hours': activity_hours,
                                                 'charged_hours': charged_hours,
                                                 'remaining_hours': activity_hours - charged_hours,
                                                 'percentage': percentage})
        return render(request, 'timepiece/reports/backlog.html', {'backlog': backlog})
    else:
        return HttpResponseRedirect( reverse('report_employee_backlog', args=(request.user.id,)) )

@permission_required('crm.view_employee_backlog')
def report_employee_backlog(request, user_id):
    """
    Determines company-wide backlog and displays
    """
    employee = User.objects.get(id=int(user_id))
    if request.user.has_perm('crm.view_backlog') or request.user==employee:
        backlog = []
        counter = -1
        for project, activity_goals in groupby(ActivityGoal.objects.filter(employee=employee, milestone__project__status=4).order_by('milestone__project__code'), lambda x: x.milestone.project):
            counter += 1
            backlog.append([])
            for activity, activity_goals in groupby(activity_goals, lambda x: x.activity):
                activity_hours = 0.0
                charged_hours = 0.0
                if activity is None:
                    activity_name = 'Other'
                    for activity_goal in activity_goals:
                        if activity_goal.date and ActivityGoal.objects.filter(employee=employee, milestone=activity_goal.milestone, date__gt=activity_goal.date, activity=activity).count():
                            # only get the latest date for this combo
                            continue
                        activity_hours += float(activity_goal.goal_hours)
                        charged_hours += float(Entry.objects.filter(project=activity_goal.milestone.project, user=employee
                            ).exclude(Q(activity__id=12)|Q(activity__id=17)|Q(activity__id=11)
                            ).aggregate(Sum('hours'))['hours__sum'] or 0.0)
                else:
                    activity_name = activity.name
                    for activity_goal in activity_goals:
                        if activity_goal.date and ActivityGoal.objects.filter(employee=employee, milestone=activity_goal.milestone, date__gt=activity_goal.date, activity=activity).count():
                            # only get the latest date for this combo
                            continue
                        activity_hours += float(activity_goal.goal_hours)
                        charged_hours += float(Entry.objects.filter(project=activity_goal.milestone.project,
                                                                    activity=activity,
                                                                    user=employee
                                                                    ).aggregate(Sum('hours'))['hours__sum'] or 0.0)
                percentage = 100.*(float(charged_hours)/float(activity_hours)) if float(activity_hours) > 0 else 0
                percentage = 100 if float(activity_hours)==0.0 else percentage
                backlog[counter].append({'activity': activity,
                                         'activity_name': activity_name,
                                         'project': project,
                                         'hours': activity_hours,
                                         'charged_hours': charged_hours,
                                         'remaining_hours': activity_hours - charged_hours,
                                         'percentage': percentage})
        context = {'backlog': backlog,
                   'employee': employee}
        return render(request, 'timepiece/reports/backlog_employee.html', context)
    else:
        return HttpResponseRedirect( reverse('report_employee_backlog', args=(request.user.id,)) )

@permission_required('crm.view_backlog')
def active_projects_burnup_charts(request, minder_id=-1):
    active_projects = Project.objects.filter(status__id=4
        ).order_by('point_person__last_name', 'point_person__first_name',
        'point_person__id', 'code')
    
    minders = []
    project_ids = []
    for minder, projects in groupby(active_projects, lambda x: x.point_person.id):
        minders.append({'minder': User.objects.get(id=minder),
                        'projects': list(projects),
                        'active_tab': True if minder==int(minder_id) else False})
    if minder_id == -1:
        minders[0]['active_tab'] = True
        project_ids = [p.id for p in minders[0]['projects']]
    else:
        project_ids = [p.id for p in active_projects.filter(point_person__id=int(minder_id))]
    
    context = {'minders': minders,
               'project_ids': project_ids}
    return render(request, 'timepiece/reports/active_projects_burnup_charts.html', context)
