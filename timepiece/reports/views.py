import csv
from dateutil.relativedelta import relativedelta
from itertools import groupby
import json
import datetime
from decimal import Decimal
import workdays
import pprint
pp = pprint.PrettyPrinter(indent=4)

from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
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

from timepiece.contracts.models import ProjectContract, ContractRate
from timepiece.entries.models import Entry, ProjectHours, Activity
from timepiece.crm.models import Project, PaidTimeOffRequest, Attribute, Milestone, Department
from timepiece.reports.forms import BillableHoursReportForm, HourlyReportForm,\
        ProductivityReportForm, PayrollSummaryReportForm, RevenueReportForm,\
        BacklogFilterForm
from timepiece.reports.utils import get_project_totals, get_payroll_totals,\
        generate_dates, get_week_window, get_company_backlog_chart_data

from timepiece.reports.utils import get_week_trunc_sunday, multikeysort
from timepiece.utils.views import cbv_decorator

from holidays.models import Holiday


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

        # If only writedowns are included
        if incl_writedown and not any((incl_billable, incl_nonbillable, incl_leave, incl_unpaid)):
            basicQ &= Q(writedown=True)
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

        if self.export_projects:
            key = 'By Project (All Projects)'
            headers = ['Project Code', 'Project Name']
        elif self.export_users:
            key = 'By User'
            headers = ['Name']

        headers.extend([date.strftime('%m/%d/%Y') for date in date_headers])
        headers.append('Total')
        content.append(headers)

        summaries = context['summaries']
        try:
            summary = filter(lambda x:x[0]==key, summaries)[0][1]
        except:
            summary = []
        for rows, totals in summary:
            for name, user_id, hours in rows:
                if self.export_projects:
                    data = name.split(': ')
                elif self.export_users:
                    data = [name]
                data.extend(hours)
                content.append(data)
            if self.export_projects:
                total = ['', 'Totals']
            elif self.export_users:
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


class RevenueReport(CSVViewMixin, TemplateView):
    template_name = 'timepiece/reports/revenue.html'

    def convert_context_to_csv(self, context):
        """Convert the context dictionary into a CSV file."""
        content = []
        if self.export_revenue_report:
            headers = ['Employee'] + context['project_headers'] + ['Employee Totals']
            content.append(headers)

            for row in context['rows']:
                content.append([row[0]] + row[2])

            content.append(['Totals'] + context['totals'])

        return content

    @property
    def defaults(self):
        """Default filter form data when no GET data is provided."""
        start = timezone.now() - relativedelta(months=1)
        start = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start + relativedelta(months=1)
        return {
            'from_date': start,
            'to_date': end,
            'trunc': 'day',
            'projects': [],
            'contracts': [],
            'employees': [],
        }

    def get(self, request, *args, **kwargs):
        self.export_revenue_report = request.GET.get(
            'export_revenue_report', False)

        context = self.get_context_data()
        if self.export_revenue_report:
            kls = CSVViewMixin
        else:
            kls = TemplateView
        return kls.render_to_response(self, context)

    def get_context_data(self, **kwargs):
        """Processes form data to get relevant entries & date_headers."""
        context = super(RevenueReport, self).get_context_data(**kwargs)

        form = self.get_form()
        if form.is_valid():
            data = form.cleaned_data
            start, end = form.save()

            # All entries must meet time period requirements.
            entryQ = Q(end_time__gte=start, end_time__lt=end)
            # for revenue, we only care about Bilalble
            entryQ &= Q(activity__billable=True, project__type__billable=True)

            # Filter by user, activity, and project type for BillableReport.
            employees = data.get('employees', [])
            projects = data.get('projects', [])
            contracts = data.get('contracts', [])
            projects_without_rates = []
            missing_rates = []
            if len(employees):
                entryQ &= Q(user__in=employees)
            if len(projects):
                entryQ &= Q(project__in=projects)
            if len(contracts):
                entryQ &= Q(project__contracts__in=contracts)

            if entryQ:
                entries = Entry.objects.filter(entryQ).order_by(
                    'user__last_name', 'user__first_name', 'user',
                    'project__code', 'activity__name', 'activity__id')
            else:
                entries = Entry.objects.none()

            revenue_totals = {}
            for user, user_entries in groupby(entries, lambda x: x.user):
                for project, user_project_entries in groupby(user_entries, lambda y: y.project):
                    # add missing project
                    if project.code not in revenue_totals:
                        revenue_totals[project.code] = {}

                    # add missing user
                    if user.id not in revenue_totals[project.code]:
                        revenue_totals[project.code][user.id] = Decimal('0.0')

                    # get the correct contract based on the time entry
                    contract = None
                    if project.contracts.count() == 1:
                        contract = project.contracts.all()[0]

                    elif project.contracts.count() > 1:
                        print 'THERE ARE MULTIPLE CONTRACTS', project.code
                        contract = project.contracts.filter(start_date__lt=end).order_by('-start_date')[0]

                    elif project.contracts.count() == 0:
                        print 'THERE ARE NO CONTRACTS', project.code
                        projects_without_rates.append(project)
                        # skip the aggregation part below because the rate is zero
                        continue

                    for activity, user_project_activity_entries in groupby(user_project_entries, lambda z: z.activity):
                        total_hours = Decimal('0.0')
                        for entry in user_project_activity_entries:
                            total_hours += entry.hours
                        try:
                            rate = ContractRate.objects.get(contract=contract, activity=activity).rate
                        except:
                            print 'contract', contract, 'activity', activity
                            missing_rates.append((contract, activity))
                            rate = Decimal('0.0')
                        total_revenue = total_hours * rate
                        revenue_totals[project.code][user.id] += total_revenue

            project_headers = sorted(revenue_totals.keys())

            rows = []
            report_columns = []
            axes = []
            project_totals = {}
            for project_code in project_headers:
                project_totals[project_code] = Decimal('0.0')
                report_columns.append([project_code])

            for user, user_entries in groupby(entries, lambda x: x.user):
                user_totals = []
                axes.append('%s, %s' % (user.last_name, user.first_name))
                for index, project_code in enumerate(project_headers):
                    user_totals.append(float(revenue_totals[project_code].get(user.id, Decimal('0.0'))))
                    project_totals[project_code] += revenue_totals[project_code].get(user.id, Decimal('0.0'))
                    report_columns[index].append(float(revenue_totals[project_code].get(user.id, Decimal('0.0'))))
                user_totals.append(sum(user_totals))
                rows.append(('%s, %s' % (user.last_name, user.first_name), user.id, user_totals))

            totals = [float(project_totals[code]) for code in sorted(project_totals.keys())]
            totals.append(sum(totals))

            report_data = {'columns': report_columns,
                           'type': 'bar',
                           'groups': [project_headers]}

            end = end - relativedelta(days=1)
            context.update({
                'from_date': start,
                'to_date': end,
                'project_headers': project_headers,
                'rows': rows,
                'totals': totals,
                'entries': entries,
                'filter_form': form,
                'projects_with_no_contracts': projects_without_rates,
                'missing_rates': missing_rates,
                'report_data': json.dumps(report_data),
                'axis_titles': json.dumps({'names': axes})
            })
        else:
            context.update({
                'from_date': None,
                'to_date': None,
                'project_headers': [],
                'entries': Entry.objects.none(),
                'filter_form': form,
                'report_data': '',
                'axis_titles': ''
            })

        return context

    def get_filename(self, context):
        request = self.request.GET.copy()
        from_date = request.get('from_date')
        to_date = request.get('to_date')
        return 'revenue_{0}_to_{1}.csv'.format(from_date, to_date)

    def get_form(self):
        data = self.request.GET or self.defaults
        data = data.copy()  # make mutable
        return RevenueReportForm(data)

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
            writedownQ, weekQ, statusQ, workQ, unpaidQ # removed the workQ because we do want Paid Lead to show up
        ).order_by('user')
    else:
        week_entries = []
        # removed the workQ because we do want Paid Lead to show up
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
        'total', overtime=True, from_date=from_date, to_date=to_date))
    # Monthly totals
    # not filter on writedown here since there should never be a writedown
    # against a PAID LEAVE project.
    leave = Entry.objects.filter(monthQ, ~workQ
                                  ).values('user', 'user__first_name',
                                  'user__last_name', 'hours', 'project__name')
    extra_values = ('project__type__label',)
    month_entries = Entry.objects.date_trunc('month', extra_values)
    month_entries_valid = month_entries.filter(monthQ, statusQ, workQ, unpaidQ, writedownQ)
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
    report_table = []
    organize_by = None

    defaults = {'writedown': False,
                # 'unpaid_time_off': False,
                'billable': True,
                'project_statuses': [a.id for a in Attribute.objects.filter(
                    type='project-status')],
                'non_billable': False,
                # 'paid_time_off': False,
                'organize_by': 'project'}
    form = ProductivityReportForm(request.GET or defaults)
    if form.is_valid():
        # only a business or a project can be set, not both.
        # if both are set, business takes precedence.
        business = form.cleaned_data['business']
        project = form.cleaned_data['project']
        project_statuses = form.cleaned_data['project_statuses']
        writedown = form.cleaned_data['writedown']
        billable = form.cleaned_data['billable']
        non_billable =form.cleaned_data['non_billable']
        # unpaid_time_off = form.cleaned_data['unpaid_time_off']
        # paid_time_off = form.cleaned_data['paid_time_off']

        organize_by = form.cleaned_data['organize_by']
        export = request.GET.get('export', False)

        if business and project:
            messages.warning(request, 'Select a Business, a Project, or neither.  Do not select both.  For this report the Business was utilized and the Project was ignored.')

        actualsQ = Q(end_time__isnull=False)
        if business:
            actualsQ &= Q(project__business=business)
            actualsQ &= Q(project__status__in=project_statuses)

        elif project:
            actualsQ &= Q(project=project)

        # filter further based on whether just billable
        # or non-billable is selected
        billableQ = Q()
        if billable and not non_billable:
            billableQ &= (Q(project__type__billable=True) &
                          Q(activity__billable=True))

        elif non_billable and not billable:
            billableQ &= (Q(project__type__billable=False) |
                          Q(activity__billable=False))

        actualsQ &= billableQ

        # exclude writedowns if it is not selected
        if not writedown:
            actualsQ &= ~Q(writedown=True)

        actuals = Entry.objects.filter(actualsQ)
        if business:
            projections = ActivityGoal.objects.filter(billableQ,
                project__business=business)
        elif project:
            projections = ActivityGoal.objects.filter(billableQ,
                project=project)
        else:
            projections = ActivityGoal.objects.filter(billableQ)

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
                        Sum('hours')).values()[0] or 0
                projected_hours = projections.filter(week_start__gte=current,
                        week_start__lt=next_week).aggregate(
                        Sum('hours')).values()[0] or 0
                report.append([date_format_filter(current, 'M j, Y'),
                        actual_hours, projected_hours, projected_hours - actual_hours])
                current = next_week

        elif organize_by == 'activity' and entry_count > 0:

            if business:
                activity_goals = ActivityGoal.objects.filter(billableQ,
                    project__business=business,
                    project__status__in=project_statuses
                    ).order_by('activity')
            elif project:
                activity_goals = ActivityGoal.objects.filter(
                    project=project).order_by('activity')
            else:
                activity_goals = ActivityGoal.objects.filter(
                    billableQ).order_by('activity')

            for activity, activity_goals in groupby(
                activity_goals, lambda x: x.activity):

                actual_hours = Decimal('0.0')
                projected_hours = Decimal('0.0')
                for activity_goal in activity_goals:
                    projected_hours += activity_goal.goal_hours
                actual_hours = actuals.filter(activity=activity).aggregate(hours=Sum('hours'))['hours']

                report.append([activity.name, actual_hours,
                    projected_hours, projected_hours - actual_hours])
                report_table.append(
                    {'label':activity.name,
                     'url': reverse('report_activity_backlog',
                        args=(activity.id,)),
                     'worked': actual_hours,
                     'assigned': projected_hours,
                     'remaining': projected_hours - actual_hours})

        elif organize_by == 'project' and entry_count > 0:

            if business:
                activity_goals = ActivityGoal.objects.filter(billableQ,
                    project__business=business,
                    project__status__in=project_statuses,
                    ).order_by('project__code')

            elif project:
                # this is not an option
                activity_goals = ActivityGoal.objects.filter(
                    project=project).order_by('project__code')

            else:
                activity_goals = ActivityGoal.objects.filter(billableQ)

            for proj, activity_goals in groupby(
                activity_goals, lambda x: x.project.code):
                actual_hours = Decimal('0.0')
                projected_hours = Decimal('0.0')
                for activity_goal in activity_goals:
                    projected_hours += activity_goal.goal_hours
                actual_hours = actuals.aggregate(hours=Sum('hours'))['hours']

                label = '%s: %s' % (activity_goal.project.code,
                    activity_goal.project.name)
                report.append([label, actual_hours,
                    projected_hours, projected_hours - actual_hours])
                report_table.append(
                    {'label':label,
                     'url': reverse('view_project',
                        args=(activity_goal.project.id,)),
                     'worked': actual_hours,
                     'assigned': projected_hours,
                     'remaining': projected_hours - actual_hours})

        elif organize_by == 'user' and entry_count > 0:
            # Determine all users who worked on or were assigned to the
            # project.
            avals = ('user', 'user__first_name', 'user__last_name')
            pvals = ('employee', 'employee__first_name', 'employee__last_name')
            ausers = list(actuals.values_list(*avals).distinct())
            pusers = list(projections.values_list(*pvals).distinct())
            key = lambda x: (x[2] + ',' + x[1]).lower()  # Sort by name
            users = sorted(list(set(ausers + pusers)), key=key)

            # Report for each user.
            for user in users:
                name = '{0}, {1}'.format(user[2], user[1])
                actual_hours = actuals.filter(user=user[0]) \
                        .aggregate(Sum('hours')).values()[0] or 0
                projected_hours = projections.filter(employee=user[0]) \
                        .aggregate(Sum('goal_hours')).values()[0] or 0
                report.append([name, actual_hours, projected_hours,
                    projected_hours - actual_hours])
                report_table.append(
                    {'label':name,
                     'url': reverse('report_employee_backlog', args=(user[0],)),
                     'worked': actual_hours,
                     'assigned': projected_hours,
                     'remaining': projected_hours - actual_hours})

        col_headers = [organize_by.title(), 'Worked Hours', 'Assigned Hours', 'Remaining Hours']
        report.insert(0, col_headers)

        if export:
            response = HttpResponse(content_type='text/csv')
            if project:
                filename = '{0}_productivity'.format(project.name)
            elif business:
                filename = '{0}_productivity'.format(business.short_name)
            else:
                filename = 'productivity'
            content_disp = 'attachment; filename={0}.csv'.format(filename)
            response['Content-Disposition'] = content_disp
            writer = csv.writer(response)
            for row in report:
                writer.writerow(row)
            return response

    return render(request, 'timepiece/reports/productivity.html', {
        'form': form,
        'report_table': report_table,
        'report': json.dumps(report, cls=DecimalEncoder),
        'type': organize_by or '',
        'total_worked': sum([r[1] for r in report[1:]]),
        'total_assigned': sum([r[2] for r in report[1:]]),
        'total_remaining': sum([r[3] for r in report[1:]]),
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

@cbv_decorator(permission_required('crm.view_employee_backlog'))
class BacklogReport(CSVViewMixin, TemplateView):
    template_name = 'timepiece/reports/backlog.html'

    def get(self, request, *args, **kwargs):
        # if user cannot see backlog, direct them to their personal backlog
        if not request.user.has_perm('crm.view_backlog'):
            return HttpResponseRedirect( reverse('report_employee_backlog', args=(request.user.id,)) )

        self.request = request

        self.active_tab = kwargs.get('active_tab', 'company') or 'company'
        self.export_data = request.GET.get('export_data', False)
        self.export_company_data = request.GET.get('export_company_data', False)

        context = self.get_context_data()
        if self.export_data or self.export_company_data:
            kls = CSVViewMixin
        else:
            kls = TemplateView
        return kls.render_to_response(self, context)

    def get_context_data(self, **kwargs):
        context = super(BacklogReport, self).get_context_data(**kwargs)

        form = self.get_form()

        if form.is_valid():
            activity_goalQ = Q(project__status__in=form.cleaned_data['project_statuses'])
            activity_goalQ &= Q(project__type__in=form.cleaned_data['project_types'])
            if form.cleaned_data['project_department']:
                activity_goalQ &= Q(project__project_department=form.cleaned_data['project_department'])
            if form.cleaned_data['projects']:
                activity_goalQ &= Q(project__in=form.cleaned_data['projects'])
            if form.cleaned_data['activities']:
                activity_goalQ &= Q(activity__in=form.cleaned_data['activities'])
            if form.cleaned_data['clients']:
                activity_goalQ &= Q(project__business__in=form.cleaned_data['clients'])

            billable = form.cleaned_data['billable']
            non_billable = form.cleaned_data['non_billable']
            if billable and not non_billable:
                activity_goalQ &= Q(project__type__billable=True, activity__billable=True)
            elif not billable and non_billable:
                activity_goalQ &= (Q(project__type__billable=False)|Q(activity__billable=False))
            elif not billable and not non_billable:
                # ensure no results are returned
                activity_goalQ &= Q(project__type__billable=True) & Q(project__type__billable=False)
        else:
            messages.warning(self.request, 'There was an error applying your selected filter.')
            activity_goalQ = Q(project__status=4)

        backlog = {}
        backlog_summary = {}
        company_total_hours = {}

        employeeQ = Q(is_active=True)
        if form.cleaned_data['project_department']:
            employeeQ &= Q(profile__department=form.cleaned_data['project_department'])

        employee_list = Group.objects.get(id=1).user_set.filter(employeeQ).order_by('last_name', 'first_name')

        for employee in employee_list:
            backlog[employee.id] = []
            backlog_summary[employee.id] = {'total_available_hours': 0,
                                            'drop_dead_date': None}
            for employee, activity_goals in groupby(
                ActivityGoal.objects.filter(activity_goalQ, employee=employee
                    ).order_by('activity'), lambda x: x.employee):

                for activity, activity_goals in groupby(activity_goals, lambda x: x.activity):
                    total_activity_hours = 0.0
                    total_charged_hours = 0.0
                    if activity is None:
                        raise Exception('Activity Goal with no Activity.')

                    activity_name = activity.name
                    if activity_name not in company_total_hours.keys():
                        company_total_hours[activity_name] = \
                            {'activity': activity,
                             'remaining_hours': 0.0}

                    for activity_goal in activity_goals:
                        total_activity_hours += float(activity_goal.goal_hours)
                        total_charged_hours += float(activity_goal.get_charged_hours)

                        backlog_summary[employee.id]['total_available_hours'] += float(activity_goal.get_remaining_hours)
                        company_total_hours[activity_name]['remaining_hours'] += float(activity_goal.get_remaining_hours)

                    percentage = 100.*(float(total_charged_hours)/float(total_activity_hours)) if float(total_activity_hours) > 0 else 0
                    percentage = 100 if float(total_activity_hours)==0.0 else percentage
                    remaining_hours = total_activity_hours - total_charged_hours
                    backlog[employee.id].append({'activity': activity,
                                                 'activity_name': activity_name,
                                                 'employee': employee,
                                                 'hours': total_activity_hours,
                                                 'charged_hours': total_charged_hours,
                                                 'remaining_hours': remaining_hours,
                                                 'percentage': percentage})

        for employee_id, values in backlog_summary.items():
            employee = User.objects.get(id=employee_id)
            backlog_summary[employee_id]['employee'] = employee
            if float(employee.profile.hours_per_week) <= 0:
                backlog_summary[employee_id]['drop_dead_date'] = datetime.date.today()
                backlog_summary[employee_id]['no_hours_per_week'] = True # why is this true?
                continue

            num_weeks = values['total_available_hours'] / float(employee.profile.hours_per_week)
            approx_days = 7 * num_weeks
            drop_dead_date = datetime.date.today() + relativedelta(days=int(approx_days))
            # backlog_summary[employee_id]['drop_dead_date'] = drop_dead_date

            future_approved_time_off = PaidTimeOffRequest.objects.filter(
                Q(status=PaidTimeOffRequest.APPROVED
                    )|Q(status=PaidTimeOffRequest.PROCESSED),
                user_profile=employee.profile,
                pto_start_date__gte=datetime.date.today(),
                pto_end_date__lte=drop_dead_date,
                ).aggregate(s=Sum('amount'))['s'] or Decimal('0.0')
            backlog_summary[employee_id]['future_approved_time_off'] = \
                future_approved_time_off

            future_holiday_time_off = Decimal('0.0')
            holidays = Holiday.holidays_between_dates(datetime.date.today(),
                drop_dead_date, {'paid_holiday': True})
            for holiday in holidays:
                future_holiday_time_off += Decimal('8.0') * \
                Decimal(employee.profile.hours_per_week) / Decimal('40.0')
            backlog_summary[employee_id]['future_holiday_time_off'] = \
                future_holiday_time_off

            total_hours = values['total_available_hours'] \
                        + float(future_holiday_time_off) \
                        + float(future_approved_time_off)

            num_weeks = total_hours / float(employee.profile.hours_per_week)
            # subtract 1 for
            approx_days = 7.0 * num_weeks - 1.0
            drop_dead_date = datetime.date.today() \
                           + relativedelta(days=int(approx_days))
            while drop_dead_date.weekday() >= 5:
                drop_dead_date -= relativedelta(days=1)
            backlog_summary[employee_id]['drop_dead_date'] = drop_dead_date

        backlog_summary_sorted = sorted(backlog_summary.values(), key=lambda x: x['drop_dead_date'])

        company_hours_per_week = Decimal('0.0')
        for u in employee_list: #.aggregate(hours=Sum('profile__hours_per_week'))['hours']
            company_hours_per_week += Decimal(u.profile.hours_per_week)
        company_hours = 0.0
        for activity_id, values in company_total_hours.items():
            company_hours += values['remaining_hours']
        num_weeks = company_hours / float(company_hours_per_week)
        approx_days = 7 * num_weeks
        drop_dead_date = datetime.date.today() + relativedelta(days=int(approx_days))

        ptoQ = Q(pto_start_date__gte=datetime.date.today(),pto_end_date__lte=drop_dead_date)
        ptoQ &= Q(status=PaidTimeOffRequest.APPROVED)|Q(status=PaidTimeOffRequest.PROCESSED)

        if form.cleaned_data['project_department']:
            ptoQ &= Q(user_profile__department=form.cleaned_data['project_department'])

        future_approved_time_off = PaidTimeOffRequest.objects.filter(ptoQ).aggregate(s=Sum('amount'))['s'] or Decimal('0.0')

        future_holiday_time_off = Decimal('0.0')
        holidays = Holiday.holidays_between_dates(datetime.date.today(),
            drop_dead_date, {'paid_holiday': True})
        for holiday in holidays:
            future_holiday_time_off += Decimal('8.0') * (
                company_hours_per_week / (Group.objects.get(id=1
                    ).user_set.filter(is_active=True).count() * \
                Decimal('40.0')))

        total_hours = company_hours \
                    + float(future_holiday_time_off) \
                    + float(future_approved_time_off)

        num_weeks = total_hours / float(company_hours_per_week)
        approx_days = 7 * num_weeks
        drop_dead_date = datetime.date.today() + relativedelta(days=int(approx_days))
        while drop_dead_date.weekday() >= 5:
            drop_dead_date -= relativedelta(days=1)
            backlog_summary[employee_id]['drop_dead_date'] = drop_dead_date

        chart_data = []
        # chart_data = {'activities': [], 'values': []}
        for activity_name, values in company_total_hours.items():
            chart_data.append([activity_name, values['remaining_hours']])
            # chart_data['activities'].append(activity_name)
            # chart_data['values'].append(values['remaining_hours'])

        company_total_hours_sorted = sorted(company_total_hours.values(), key=lambda x: -1*x['remaining_hours'])
        company_backlog = {
            'company_total_hours': company_total_hours_sorted,
            'company_work_hours': company_hours,
            'company_total_hours_with_time_off': total_hours,
            'drop_dead_date': drop_dead_date,
            'company_hours': company_hours,
            'future_approved_time_off': future_approved_time_off,
            'future_holiday_time_off': future_holiday_time_off,
            'chart_data': json.dumps(chart_data)
        }

        total_company_hours = 0.0
        for activity_hours in company_backlog['company_total_hours']:
            total_company_hours += activity_hours['remaining_hours']

        company_backlog_data, export_filters = get_company_backlog_chart_data(activity_goalQ)
        no_data = True
        filters = {}
        if 'filters' in company_backlog_data:
            filters = company_backlog_data['filters']
            no_data = False

        context.update({
            'backlog': backlog,
            'backlogfilter_form': form,
            'backlog_summary': backlog_summary_sorted,
            'company_backlog': company_backlog,
            'total_company_hours': total_company_hours,
            'active_tab': self.active_tab,
            'company_backlog_data': company_backlog_data,
            'export_filters': export_filters,
            'chart_data': json.dumps(company_backlog_data),
            'filters': filters,
            'no_data': no_data})

        return context

    def convert_context_to_csv(self, context):
        """Convert the context dictionary into a CSV file."""
        content = []
        if self.export_data:
            headers = ['Activity Code', 'Activity Name', 'Remaining Hours']
            content.append(headers)
            total_hours = 0.0
            for activity_hours in context['company_backlog']['company_total_hours']:
                row = [activity_hours['activity'].code,
                       activity_hours['activity'].name,
                       activity_hours['remaining_hours']]
                content.append(row)
                total_hours += activity_hours['remaining_hours']
            row = ['', 'TOTAL', total_hours]
            content.append(row)
        elif self.export_company_data:
            data = context['company_backlog_data']
            export_filters = context['export_filters']
            headers = ['Activity Code', 'Activity Name', 'Project Code',
                'Project Name', 'Project Status', 'Project Type', 'Billable',
                'Business Short Name', 'Business Name', 'Remaining Hours']
            text_col_count=len(headers)-1
            if not data:
                content.append(headers)
                return content
            headers.extend(data['columns'][0][1:])
            content.append(headers)
            for col in data['columns'][1:]:
                key = col[0]
                if key == 'Total Avg Hours':
                    continue
                if key == 'Utilization Avg Hours':
                    continue
                hours = sum(col[1:])
                row_data = export_filters[key]
                row = [row_data['activity'].code,
                       row_data['activity'].name,
                       row_data['project'].code,
                       row_data['project'].name,
                       row_data['project'].status.label,
                       row_data['project'].type.label,
                       row_data['billable'],
                       row_data['client'].short_name,
                       row_data['client'].name,
                       hours]
                for hours in col[1:]:
                    row.append(hours)
                content.append(row)
            totals_row=['-']*text_col_count
            totals_row.extend([sum(x) for x in zip(*content[1:])[text_col_count:]])
            content.append(totals_row)
        return content

    @property
    def defaults(self):
        """Default filter form data when no GET data is provided."""
        return {'billable': True,
                'non_billable': True,
                'project_statuses': [4],
                'project_types': [a.id for a in Attribute.objects.filter(
                    type='project-type')],
                'project_department': None,
                'projects': None,
                'activities': None}

    def get_form(self):
        data = self.request.GET or self.defaults
        data = data.copy()  # make mutable
        # Fix booleans - the strings "0" and "false" are True in Python
        # for key in ['billable', 'non_billable', 'paid_time_off', 'unpaid_time_off', 'writedown']:
        #     data[key] = key in data and \
        #                 str(data[key]).lower() in ('on', 'true', '1')

        return BacklogFilterForm(data)

    def get_filename(self, context):
        return 'backlog_totals_by_activity.csv'.format()

# @permission_required('crm.view_employee_backlog')
# def report_backlog(request, active_tab='company'):
#     """
#     Determines company-wide backlog and displays
#     """
#     if request.user.has_perm('crm.view_backlog'):
#         defaults = {'billable': True,
#                     'non_billable': True,
#                     'project_statuses': [4],
#                     'project_types': [a.id for a in Attribute.objects.filter(
#                         type='project-type')],
#                     'projects': None,
#                     'activities': None}
#         form = BacklogFilterForm(request.GET or defaults)
#         if form.is_valid():
#             activity_goalQ = Q(project__status__in=form.cleaned_data['project_statuses'])
#             activity_goalQ &= Q(project__type__in=form.cleaned_data['project_types'])
#             if form.cleaned_data['projects']:
#                 activity_goalQ &= Q(project__in=form.cleaned_data['projects'])
#             if form.cleaned_data['activities']:
#                 activity_goalQ &= Q(activity__in=form.cleaned_data['activities'])

#             billable = form.cleaned_data['billable']
#             non_billable = form.cleaned_data['non_billable']
#             if billable and not non_billable:
#                 activity_goalQ &= Q(project__billable=True, activity__billable=True)
#             elif not billable and non_billable:
#                 activity_goalQ &= (Q(project__billable=False)|Q(activity__billable=False))
#             elif not billable and not non_billable:
#                 # ensure no results are returned
#                 activity_goalQ &= Q(project__billable=True) & Q(project__billable=False)
#         else:
#             messages.warning(request, 'There was an error applying your selected filter.')
#             activity_goalQ = Q(project__status=4)

#         backlog = {}
#         backlog_summary = {}
#         company_total_hours = {}
#         for employee in Group.objects.get(id=1).user_set.filter(is_active=True).order_by('last_name', 'first_name'):
#             backlog[employee.id] = []
#             backlog_summary[employee.id] = {'total_available_hours': 0,
#                                             'drop_dead_date': None}
#             for employee, activity_goals in groupby(
#                 ActivityGoal.objects.filter(activity_goalQ, employee=employee
#                     ).order_by('activity'), lambda x: x.employee):

#                 for activity, activity_goals in groupby(activity_goals, lambda x: x.activity):
#                     total_activity_hours = 0.0
#                     total_charged_hours = 0.0
#                     if activity is None:
#                         raise Exception('Activity Goal with no Activity.')

#                     activity_name = activity.name
#                     if activity_name not in company_total_hours.keys():
#                         company_total_hours[activity_name] = \
#                             {'activity': activity,
#                              'remaining_hours': 0.0}

#                     for activity_goal in activity_goals:
#                         total_activity_hours += float(activity_goal.goal_hours)
#                         total_charged_hours += float(activity_goal.get_charged_hours)

#                         backlog_summary[employee.id]['total_available_hours'] += float(activity_goal.get_remaining_hours)
#                         company_total_hours[activity_name]['remaining_hours'] += float(activity_goal.get_remaining_hours)

#                     percentage = 100.*(float(total_charged_hours)/float(total_activity_hours)) if float(total_activity_hours) > 0 else 0
#                     percentage = 100 if float(total_activity_hours)==0.0 else percentage
#                     remaining_hours = total_activity_hours - total_charged_hours
#                     backlog[employee.id].append({'activity': activity,
#                                                  'activity_name': activity_name,
#                                                  'employee': employee,
#                                                  'hours': total_activity_hours,
#                                                  'charged_hours': total_charged_hours,
#                                                  'remaining_hours': remaining_hours,
#                                                  'percentage': percentage})

#         for employee_id, values in backlog_summary.items():
#             employee = User.objects.get(id=employee_id)
#             backlog_summary[employee_id]['employee'] = employee
#             if float(employee.profile.hours_per_week) <= 0:
#                 backlog_summary[employee_id]['drop_dead_date'] = datetime.date.today()
#                 backlog_summary[employee_id]['no_hours_per_week'] = True
#                 continue

#             num_weeks = values['total_available_hours'] / float(employee.profile.hours_per_week)
#             approx_days = 7 * num_weeks
#             drop_dead_date = datetime.date.today() + relativedelta(days=int(approx_days))
#             # backlog_summary[employee_id]['drop_dead_date'] = drop_dead_date

#             future_approved_time_off = PaidTimeOffRequest.objects.filter(
#                 Q(status=PaidTimeOffRequest.APPROVED
#                     )|Q(status=PaidTimeOffRequest.PROCESSED),
#                 user_profile=employee.profile,
#                 pto_start_date__gte=datetime.date.today(),
#                 pto_end_date__lte=drop_dead_date,
#                 ).aggregate(s=Sum('amount'))['s'] or Decimal('0.0')
#             backlog_summary[employee_id]['future_approved_time_off'] = \
#                 future_approved_time_off

#             future_holiday_time_off = Decimal('0.0')
#             holidays = Holiday.holidays_between_dates(datetime.date.today(),
#                 drop_dead_date, {'paid_holiday': True})
#             for holiday in holidays:
#                 future_holiday_time_off += Decimal('8.0') * \
#                 Decimal(employee.profile.hours_per_week) / Decimal('40.0')
#             backlog_summary[employee_id]['future_holiday_time_off'] = \
#                 future_holiday_time_off

#             total_hours = values['total_available_hours'] \
#                         + float(future_holiday_time_off) \
#                         + float(future_approved_time_off)

#             num_weeks = total_hours / float(employee.profile.hours_per_week)
#             # subtract 1 for
#             approx_days = 7.0 * num_weeks - 1.0
#             drop_dead_date = datetime.date.today() \
#                            + relativedelta(days=int(approx_days))
#             while drop_dead_date.weekday() >= 5:
#                 drop_dead_date -= relativedelta(days=1)
#             backlog_summary[employee_id]['drop_dead_date'] = drop_dead_date

#         backlog_summary_sorted = sorted(backlog_summary.values(), key=lambda x: x['drop_dead_date'])

#         company_hours_per_week = Decimal('0.0')
#         for u in Group.objects.get(id=1).user_set.filter(is_active=True): #.aggregate(hours=Sum('profile__hours_per_week'))['hours']
#             company_hours_per_week += Decimal(u.profile.hours_per_week)
#         company_hours = 0.0
#         for activity_id, values in company_total_hours.items():
#             company_hours += values['remaining_hours']
#         num_weeks = company_hours / float(company_hours_per_week)
#         approx_days = 7 * num_weeks
#         drop_dead_date = datetime.date.today() + relativedelta(days=int(approx_days))

#         future_approved_time_off = PaidTimeOffRequest.objects.filter(
#                 Q(status=PaidTimeOffRequest.APPROVED
#                     )|Q(status=PaidTimeOffRequest.PROCESSED),
#                 pto_start_date__gte=datetime.date.today(),
#                 pto_end_date__lte=drop_dead_date,
#                 ).aggregate(s=Sum('amount'))['s'] or Decimal('0.0')

#         future_holiday_time_off = Decimal('0.0')
#         holidays = Holiday.holidays_between_dates(datetime.date.today(),
#             drop_dead_date, {'paid_holiday': True})
#         for holiday in holidays:
#             future_holiday_time_off += Decimal('8.0') * (
#                 company_hours_per_week / (Group.objects.get(id=1
#                     ).user_set.filter(is_active=True).count() * \
#                 Decimal('40.0')))

#         total_hours = company_hours \
#                     + float(future_holiday_time_off) \
#                     + float(future_approved_time_off)

#         num_weeks = total_hours / float(company_hours_per_week)
#         approx_days = 7 * num_weeks
#         drop_dead_date = datetime.date.today() + relativedelta(days=int(approx_days))
#         while drop_dead_date.weekday() >= 5:
#             drop_dead_date -= relativedelta(days=1)
#             backlog_summary[employee_id]['drop_dead_date'] = drop_dead_date

#         chart_data = []
#         # chart_data = {'activities': [], 'values': []}
#         for activity_name, values in company_total_hours.items():
#             chart_data.append([activity_name, values['remaining_hours']])
#             # chart_data['activities'].append(activity_name)
#             # chart_data['values'].append(values['remaining_hours'])

#         company_total_hours_sorted = sorted(company_total_hours.values(), key=lambda x: -1*x['remaining_hours'])
#         company_backlog = {
#             'company_total_hours': company_total_hours_sorted,
#             'company_work_hours': company_hours,
#             'company_total_hours_with_time_off': total_hours,
#             'drop_dead_date': drop_dead_date,
#             'company_hours': company_hours,
#             'future_approved_time_off': future_approved_time_off,
#             'future_holiday_time_off': future_holiday_time_off,
#             'chart_data': json.dumps(chart_data)
#         }

#         return render(request, 'timepiece/reports/backlog.html',
#             {'backlog': backlog,
#              'backlogfilter_form': form,
#              'backlog_summary': backlog_summary_sorted,
#              'company_backlog': company_backlog,
#              'active_tab': active_tab or 'company'})
#     else:
#         return HttpResponseRedirect( reverse('report_employee_backlog', args=(request.user.id,)) )

@permission_required('crm.view_backlog')
def report_activity_backlog(request, activity_id):
    """
    Determines company-wide backlog and displays
    """
    if int(activity_id):
        activity = Activity.objects.get(id=int(activity_id))
        project_list = list(set([ag.project for ag in ActivityGoal.objects.filter(project__status=4, activity=activity)]))
        backlog = []

        for project in project_list:
            employees = list(set([ag.employee for ag in ActivityGoal.objects.filter(project=project, activity=activity)]))
            if None in employees:
                charged_hours = Entry.objects.filter(
                    activity=activity, project=project).aggregate(
                    hours=Sum('hours'))['hours'] or 0.0
            else:
                charged_hours = Entry.objects.filter(
                    activity=activity, project=project, user__in=employees
                    ).aggregate(hours=Sum('hours'))['hours'] or 0.0
            activity_hours = ActivityGoal.objects.filter(
                project=project, activity=activity
                ).aggregate(hours=Sum('goal_hours'))['hours']

            percentage = 100.*(float(charged_hours)/float(activity_hours)) if float(activity_hours) > 0 else 0
            percentage = 100 if float(activity_hours)==0.0 else percentage
            backlog.append({'activity': activity,
                            'activity_name': activity.name,
                            'project': project,
                            'hours': activity_hours,
                            'charged_hours': charged_hours,
                            'remaining_hours': float(activity_hours) - float(charged_hours),
                            'percentage': percentage})

        sorted_backlog = sorted(backlog, key=lambda x: -1*x['percentage'])
        context = {'backlog': sorted_backlog,
                   'activity': activity,
                   'activity_name': activity.name}
        return render(request, 'timepiece/reports/backlog_activity.html', context)
    else:
        activity = None
    backlog = []
    counter = -1
    for project, activity_goals in groupby(ActivityGoal.objects.filter(
        activity=activity, project__status=4).order_by(
        'project__code'), lambda x: x.milestone.project):

        for activity, activity_goals in groupby(activity_goals, lambda x: x.activity):
            activity_hours = 0.0
            charged_hours = 0.0
            if activity is None:
                activity_name = 'Other'
                exclude_Q = Q()
                for activity_goal in activity_goals:
                    #if activity_goal.date and ActivityGoal.objects.filter(milestone=activity_goal.milestone, date__gt=activity_goal.date, activity=activity).count():
                        # only get the latest date for this combo
                    #    continue
                    activity_hours += float(activity_goal.goal_hours)
                    for ag in ActivityGoal.objects.filter(project=activity_goal.project, activity__isnull=False):
                        exclude_Q |= Q(activity__id=ag.activity.id)
                charged_hours += float(Entry.objects.filter(project=activity_goal.project, project__status=4
                    ).exclude(exclude_Q).aggregate(Sum('hours'))['hours__sum'] or 0.0)
            else:
                activity_name = activity.name
                for activity_goal in activity_goals:
                    #if activity_goal.date and ActivityGoal.objects.filter(milestone=activity_goal.milestone, date__gt=activity_goal.date, activity=activity).count():
                        # only get the latest date for this combo
                    #    continue
                    activity_hours += float(activity_goal.goal_hours)
                charged_hours = float(Entry.objects.filter(
                    project=activity_goal.milestone.project, activity=activity, project__status=4
                    ).aggregate(Sum('hours'))['hours__sum'] or 0.0)
            percentage = 100.*(float(charged_hours)/float(activity_hours)) if float(activity_hours) > 0 else 0
            percentage = 100 if float(activity_hours)==0.0 else percentage
            backlog.append({'activity': activity,
                            'activity_name': activity_name,
                            'project': project,
                            'hours': activity_hours,
                            'charged_hours': charged_hours,
                            'remaining_hours': activity_hours - charged_hours,
                            'percentage': percentage})
    context = {'backlog': backlog,
               'activity': activity}
    return render(request, 'timepiece/reports/backlog_activity.html', context)

@permission_required('crm.view_employee_backlog')
def report_employee_backlog(request, user_id):
    """
    Determines individual backlog and displays
    """
    employee = User.objects.get(id=int(user_id))
    activitygoal_projects = list(Project.objects.filter(
        id__in=utils.get_setting('TIMEPIECE_PAID_LEAVE_PROJECTS').values() + \
        utils.get_setting('TIMEPIECE_UNPAID_LEAVE_PROJECTS').values()))

    if request.user.has_perm('crm.view_backlog') or request.user==employee:
        backlog = []
        counter = -1
        for project, activity_goals in groupby(ActivityGoal.objects.filter(
            employee=employee, project__status=utils.get_setting(
                'TIMEPIECE_DEFAULT_PROJECT_STATUS')
            ).order_by('project__code', 'activity__name', 'activity__id'
            ), lambda x: x.project):

            activitygoal_projects.append(project)
            counter += 1
            backlog.append({'project': project,
                            'activity_goals': []})
            # backlog.append({'project': project,
            #                 'activity_goals': list(activity_goals)})
            activity_exclude_Q = Q()
            for activity, activity_goals in groupby(activity_goals, lambda x: x.activity):
                activity_exclude_Q |= Q(activity=activity)
                dates_exclude_Q = Q()
                for activity_goal in activity_goals:
                    backlog[counter]['activity_goals'].append(activity_goal)
                    dates_exclude_Q |= Q(start_time__gte=datetime.datetime.combine(activity_goal.date, datetime.time.min),
                                         start_time__lt=datetime.datetime.combine(activity_goal.end_date, datetime.time.max))

                # add missing date ranges for existing Project+Employee+Activity
                missing_entries = Entry.objects.filter(
                    project=project, user=employee, activity=activity
                    ).exclude(dates_exclude_Q
                    ).aggregate(hours=Sum('hours'), earliest=Min('start_time'), latest=Max('start_time'))
                    # ).annotate(earliest=Min('start_time')
                    # ).annotate(latest=Max('start_time'))
                if missing_entries['hours']:
                    backlog[counter]['activity_goals'].append(
                        {'id': None,
                         'activity': activity,
                         'project': project,
                         'employee': employee,
                         'goal_hours': 0.0,
                         'date': missing_entries['earliest'].date(),
                         'end_date': missing_entries['latest'].date(),
                         'get_charged_hours': missing_entries['hours'],
                         'get_remaining_hours': -1*missing_entries['hours'],
                         'get_percent_complete': 100.0})

            # add missing activity goals for this Project+Employee+Activity
            for activity_sum in Entry.objects.filter(project=project, user=employee
                ).exclude(activity_exclude_Q).values('activity'
                ).annotate(hours=Sum('hours')).order_by('-hours'):

                activity = Activity.objects.get(id=activity_sum['activity'])
                start_date = Entry.objects.filter(
                    project=project, user=employee, activity=activity
                    ).values('start_time').order_by('start_time'
                    )[0]['start_time'].date()
                try:
                    end_date = Entry.objects.filter(
                        project=project, user=employee, activity=activity
                        ).values('end_time').order_by('-end_time'
                        )[0]['end_time'].date()
                except:
                    end_date = datetime.date.today()

                backlog[counter]['activity_goals'].append(
                    {'id': None,
                     'activity': activity,
                     'project': project,
                     'employee': employee,
                     'goal_hours': 0.0,
                     'date': start_date,
                     'end_date': end_date,
                     'get_charged_hours': activity_sum['hours'],
                     'get_remaining_hours': -1*activity_sum['hours'],
                     'get_percent_complete': 100.0})

        # add missing projects
        for entry in Entry.objects.filter(
            project__status=utils.get_setting(
                'TIMEPIECE_DEFAULT_PROJECT_STATUS'),
            user=employee
            ).exclude(project__in=activitygoal_projects
            ).values('project__code').order_by('project__code'
            ).distinct('project__code'):

            counter += 1
            project = Project.objects.get(code=entry['project__code'])
            backlog.append({'project': project,
                            'activity_goals': []})
            for entry2 in Entry.objects.filter(
                project=project, user=employee).values('activity__id'
                ).order_by('activity__id').distinct('activity__id'):

                activity = Activity.objects.get(id=entry2['activity__id'])
                entries_summary = Entry.objects.filter(project=project,
                    activity=activity, user=employee
                    ).aggregate(hours=Sum('hours'),
                    start_date=Min('start_time'), end_date=Max('end_time'))
                if entries_summary['end_date'] is None:
                    print 'got here', entries_summary
                    entries_summary['end_date'] = datetime.datetime.now()
                activity_hours = Decimal('0.0')
                backlog[counter]['activity_goals'].append(
                    {'activity': activity,
                     'project': project,
                     'date': entries_summary['start_date'].date(),
                     'end_date': entries_summary['end_date'].date(),
                     'goal_hours': activity_hours,
                     'get_charged_hours': entries_summary['hours'],
                     'get_remaining_hours': activity_hours - entries_summary['hours'],
                     'get_percent_complete': 100})

        if employee.profile.hours_per_week == 0:
            message = '{0} {1} has no schedule set in their profile.  Set their expected hours for each day of the week for an accurate backlog.'.format(
                    employee.first_name, employee.last_name)
            messages.error(request, message)

        context = {'backlog': backlog,
                   'employee': employee,
                   'chart_data': json.dumps(get_employee_backlog_chart_data(user_id))}
        return render(request, 'timepiece/reports/backlog_employee.html', context)
    else:
        return HttpResponseRedirect( reverse('report_employee_backlog', args=(request.user.id,)) )


@permission_required('crm.view_employee_backlog')
def report_all_employee_backlog(request):


    departments = {}
    for d,d_pretty in Department.DEPARTMENTS: #TODO update with department as a model
        dept_emps = Group.objects.get(id=1).user_set.filter(is_active=True,profile__department=d).order_by('last_name', 'first_name')
        charts={}
        for e in dept_emps:
            charts[e]=json.dumps(get_employee_backlog_chart_data(e.id))
        if len(dept_emps) > 0:
            departments[d_pretty] = charts


    #
    #
    # employees=Group.objects.get(id=1).user_set.filter(is_active=True).order_by('last_name', 'first_name')
    #
    # charts={}
    # for e in employees:
    #     charts[e]=json.dumps(get_employee_backlog_chart_data(e.id))

    context = {'departments':departments}

    return render(request, 'timepiece/reports/backlog_employee_all.html', context)




def get_employee_backlog_chart_data(user_id):
    """
    Creates the data objects required by the c3 frond-end visualization
    """

    def new_empty_date():
        # return {'Holiday': 0.0,
        #         'Approved Time Off': 0.0}
        return {}

    employee = User.objects.get(id=int(user_id))

    # get weekly schedule, starting Monday
    week_schedule = employee.profile.week_schedule
    week_schedule.append(week_schedule.pop(0))
    # create a tuple of the weekend day indices
    weekends = []
    for dow, hours in enumerate(week_schedule):
        if hours == 0.0:
            weekends.append(dow)
    weekends = tuple(weekends)

    days_per_week = (Decimal('7.0') - Decimal(len(weekends)))
    if days_per_week == Decimal('0.0'):
        avg_hours_per_day = Decimal('8.0')
    else:
        avg_hours_per_day = Decimal(employee.profile.hours_per_week) / \
            (Decimal('7.0') - Decimal(len(weekends)))
    coverage = {}
    billable_coverage = {}

    start_week = utils.get_week_start(datetime.date.today()).date()
    start_week = datetime.date.today()
    activity_goals = ActivityGoal.objects.filter(
        employee=employee, end_date__gte=start_week,
        project__status=utils.get_setting(
            'TIMEPIECE_DEFAULT_PROJECT_STATUS'))

    if activity_goals.count() == 0:
         return {}

    # determine the end date and add one more week to show clearly that
    # the employee has no coverage then
    end_date = max(
        utils.get_bimonthly_dates(datetime.date.today())[1].date(),
        activity_goals.aggregate(end_date=Max('end_date'))['end_date'])
    end_week = utils.get_week_start(end_date).date() \
              + datetime.timedelta(days=7)

    # get total number of weeks shown on plot; this equals the
    # length of the arrays
    num_weeks = (end_week - start_week).days / 7 + 1

    # determine holidays and add time (whether paid or not)
    holidays = [h['date'] for h in Holiday.holidays_between_dates(
        start_week, end_week, {'paid_holiday': True})]
    for holiday in holidays:
        if str(holiday) not in coverage:
            coverage[str(holiday)] = new_empty_date()
        coverage[str(holiday)]['Holiday'] = float(avg_hours_per_day)

    # add Time Off requests as holidays
    # TODO: should make this smarter so that if it is a partial day it
    #       does not count as a full day
    print 'start week', start_week
    print 'end week', end_week
    for ptor in employee.profile.paidtimeoffrequest_set.filter(
        Q(pto_start_date__gte=start_week)|Q(pto_end_date__gte=end_week),
        Q(status='approved')|Q(status='processed')):

        print 'ptor', ptor
        num_workdays = max(workdays.networkdays(ptor.pto_start_date,
            ptor.pto_end_date, holidays=holidays, weekends=weekends), 1)
        ptor_hours_per_day = ptor.amount / Decimal(num_workdays)

        for i in range((ptor.pto_end_date-ptor.pto_start_date).days + 1):
            date = ptor.pto_start_date + datetime.timedelta(days=i)
            if date.weekday() not in weekends:
                holidays.append(date)
                if str(date) not in coverage:
                    coverage[str(date)] = \
                        new_empty_date()
                coverage[str(date)]['Approved Time Off'] = \
                    float(ptor_hours_per_day)

            # elif date.weekday() < 5:
            #     holidays.append(date)
            #     if str(date) not in coverage:
            #         coverage[str(date)] = \
            #             new_empty_date()


    y_axes = {'Holiday': ['data1'],
              'Approved Time Off': ['data2']}
    data_counter = 3
    for activity_goal in activity_goals:
        if activity_goal.project.code not in y_axes.keys():
            y_axes[activity_goal.project.code] = ['data%s'%data_counter]
            data_counter += 1

        start_date = start_week if activity_goal.date < start_week \
            else activity_goal.date

        end_date = activity_goal.end_date
        num_workdays = max(workdays.networkdays(start_date, end_date,
            holidays=holidays, weekends=weekends), 1)
        ag_hours_per_workday = activity_goal.get_remaining_hours / Decimal(num_workdays)

        for i in range((end_date-start_date).days + 1):
            date = start_date + datetime.timedelta(days=i)
            if workdays.networkdays(date, date, holidays=holidays,
                weekends=weekends):

                if str(date) not in coverage:
                    coverage[str(date)] = new_empty_date()
                if str(date) not in billable_coverage:
                    billable_coverage[str(date)] = 0.0
                if activity_goal.project.code not in coverage[str(date)]:
                    coverage[str(date)][activity_goal.project.code] = 0.0
                coverage[str(date)][activity_goal.project.code] += \
                    float(ag_hours_per_workday)
                if activity_goal.project.type.billable and activity_goal.activity.billable:
                    billable_coverage[str(date)] += float(ag_hours_per_workday)

            elif workdays.networkdays(date, date, holidays=holidays,
                weekends=(5,6)):

                if str(date) not in coverage:
                    coverage[str(date)] = new_empty_date()
                    billable_coverage[str(date)] = 0.0
                if activity_goal.project.code not in coverage[str(date)]:
                    coverage[str(date)][activity_goal.project.code] = 0.0

    columns = {'x': []}
    for date in sorted(coverage.keys()):
        columns['x'].append(date)
        for proj, hours in coverage[date].items():
            if proj not in columns:
                columns[proj] = [0.0] * (len(columns['x']) - 1)
            columns[proj].append(hours)

        expected_len = len(columns['x'])
        for check_key, vals in columns.items():
            while len(vals) != expected_len:
                columns[check_key].append(0.0)

    c3_columns = []
    for proj, vals in columns.items():
        if proj != 'x':
            c3_columns.append([proj] + vals)
        else:
            c3_columns.insert(0, [proj] + vals)
    schedule = ['Total Avg Hours']
    utilization = ['Utilization Avg Hours']
    week_dict = employee.profile.week_dict()
    for date_str in sorted(coverage.keys()):
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d', ).date()
        schedule.append(week_dict[date.weekday()])
        utilization.append(week_dict[date.weekday()]*employee.profile.get_utilization)

    # c3_columns.append(['Regular Schedule'] + [float(avg_hours_per_day)]*len(columns['x']))
    c3_columns.append(schedule)
    c3_columns.append(utilization)
    keys = columns.keys()
    keys.remove('x')
    data = {'columns': c3_columns,
            'keys': keys,
            'avg_hours': float(avg_hours_per_day)}
    return data

@permission_required('crm.view_employee_backlog')
def employee_backlog_chart_data(request, user_id):
    if request.user.has_perm('crm.view_backlog') or request.user==employee:
        return HttpResponse(json.dumps(get_employee_backlog_chart_data(user_id)),
            status=200, mimetype='application/json')

@permission_required('crm.view_backlog')
def report_overrun_backlog(request):
    """
    Finds all activity goals that are overrun
    """
    project_status = request.GET.get('project_status',
        utils.get_setting('TIMEPIECE_DEFAULT_PROJECT_STATUS'))
    backlog = []
    employee_counter = -1
    # for activity_goal in ActivityGoal.objects.filter(
    #     project__status=project_status):

    #     if not activity_goal.goal_overrun:
    #         continue

    #     backlog.append(activity_goal)
    for employee in Group.objects.get(id=1).user_set.filter(is_active=True
        ).order_by('last_name', 'first_name'):

        employee_counter += 1
        backlog.append({'employee': employee,
                        'projects': []})
        activitygoal_projects = list(Project.objects.filter(
            id__in=utils.get_setting('TIMEPIECE_PAID_LEAVE_PROJECTS').values() + \
            utils.get_setting('TIMEPIECE_UNPAID_LEAVE_PROJECTS').values()))
        # activitygoal_projects = []
        project_counter = -1

        for project, activity_goals in groupby(ActivityGoal.objects.filter(
            employee=employee, project__status=project_status
            ).order_by('project__code', 'activity__name', 'activity__id'
            ), lambda x: x.project):

            activitygoal_projects.append(project)
            project_counter += 1
            backlog[employee_counter]['projects'].append(
                {'project': project,
                 'activity_goals': []})

            activity_exclude_Q = Q()
            for activity, activity_goals in groupby(activity_goals, lambda x: x.activity):
                activity_exclude_Q |= Q(activity=activity)
                dates_exclude_Q = Q()
                for activity_goal in activity_goals:
                    if activity_goal.goal_overrun:
                        print activity_goal
                        backlog[employee_counter]['projects'][project_counter
                            ]['activity_goals'].append(activity_goal)
                    dates_exclude_Q |= Q(start_time__gte=datetime.datetime.combine(activity_goal.date, datetime.time.min),
                                         start_time__lt=datetime.datetime.combine(activity_goal.end_date, datetime.time.max))

                # add missing date ranges for existing Project+Employee+Activity
                missing_entries = Entry.objects.filter(
                    project=project, user=employee, activity=activity
                    ).exclude(dates_exclude_Q
                    ).aggregate(hours=Sum('hours'), earliest=Min('start_time'), latest=Max('start_time'))
                if missing_entries['hours']:
                    backlog[employee_counter]['projects'][project_counter][
                        'activity_goals'].append(
                            {'id': None,
                             'activity': activity,
                             'project': project,
                             'employee': employee,
                             'goal_hours': 0.0,
                             'date': missing_entries['earliest'].date(),
                             'end_date': missing_entries['latest'].date(),
                             'get_charged_hours': missing_entries['hours'],
                             'get_remaining_hours': -1*missing_entries['hours'],
                             'get_percent_complete': 100.0})

            # add missing activity goals for this Project+Employee+Activity
            for activity_sum in Entry.objects.filter(project=project, user=employee
                ).exclude(activity_exclude_Q).values('activity'
                ).annotate(hours=Sum('hours')).order_by('-hours'):

                activity = Activity.objects.get(id=activity_sum['activity'])
                start_date = Entry.objects.filter(
                    project=project, user=employee, activity=activity
                    ).values('start_time').order_by('start_time'
                    )[0]['start_time'].date()
                try:
                    end_date = Entry.objects.filter(
                        project=project, user=employee, activity=activity
                        ).values('end_time').order_by('-end_time'
                        )[0]['end_time'].date()
                except:
                    end_date = datetime.date.today()

                backlog[employee_counter]['projects'][project_counter][
                    'activity_goals'].append(
                        {'id': None,
                         'activity': activity,
                         'project': project,
                         'employee': employee,
                         'goal_hours': 0.0,
                         'date': start_date,
                         'end_date': end_date,
                         'get_charged_hours': activity_sum['hours'],
                         'get_remaining_hours': -1*activity_sum['hours'],
                         'get_percent_complete': 100.0})

        # add missing projects
        for entry in Entry.objects.filter(
            project__status=utils.get_setting(
                'TIMEPIECE_DEFAULT_PROJECT_STATUS'),
            user=employee
            ).exclude(project__in=activitygoal_projects
            ).values('project__code').order_by('project__code'
            ).distinct('project__code'):

            project_counter += 1
            project = Project.objects.get(code=entry['project__code'])
            backlog[employee_counter]['projects'].append(
                {'project': project,
                 'activity_goals': []})
            for entry2 in Entry.objects.filter(
                project=project, user=employee).values('activity__id'
                ).order_by('activity__id').distinct('activity__id'):

                activity = Activity.objects.get(id=entry2['activity__id'])
                entries_summary = Entry.objects.filter(project=project,
                    activity=activity, user=employee
                    ).aggregate(hours=Sum('hours'),
                    start_date=Min('start_time'), end_date=Max('end_time'))
                if entries_summary['end_date'] is None:
                    entries_summary['end_date'] = datetime.datetime.now()
                activity_hours = Decimal('0.0')
                backlog[employee_counter]['projects'][project_counter][
                    'activity_goals'].append(
                        {'activity': activity,
                         'project': project,
                         'date': entries_summary['start_date'].date(),
                         'end_date': entries_summary['end_date'].date(),
                         'goal_hours': activity_hours,
                         'get_charged_hours': entries_summary['hours'],
                         'get_remaining_hours': activity_hours - entries_summary['hours'],
                         'get_percent_complete': 100})

    context = {'backlog': backlog}
    return render(request, 'timepiece/reports/backlog_overrun.html', context)

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


class PendingMilestonesReport(TemplateView):
    template_name = 'timepiece/reports/milestones.html'

    def get_context_data(self, **kwargs):
        context = super(PendingMilestonesReport, self).get_context_data(**kwargs)
        pending_milestones = []
        for project, milestones in groupby(
            Milestone.objects.filter(status__in=[Milestone.NEW, Milestone.MODIFIED],
                project__status=4), lambda m:m.project):

            pending_milestones.append((project, list(milestones)))

        context['pending_milestones'] = pending_milestones
        return context
